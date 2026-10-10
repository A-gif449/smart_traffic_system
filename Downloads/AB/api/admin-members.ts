import { cert, getApps, initializeApp } from 'firebase-admin/app'
import { getAuth } from 'firebase-admin/auth'
import { createClient } from '@supabase/supabase-js'

function authAdmin(){const projectId=process.env.FIREBASE_PROJECT_ID||process.env.VITE_FIREBASE_PROJECT_ID;const clientEmail=process.env.FIREBASE_CLIENT_EMAIL;const privateKey=process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g,'\n');if(!projectId||!clientEmail||!privateKey)throw new Error('Firebase Admin credentials are not configured.');if(!getApps().length)initializeApp({credential:cert({projectId,clientEmail,privateKey})});return getAuth()}
function db(){const url=process.env.SUPABASE_URL||process.env.VITE_SUPABASE_URL;const key=process.env.SUPABASE_SERVICE_ROLE_KEY;if(!url||!key)throw new Error('Supabase server credentials are not configured.');return createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}})}
function json(res:any,status:number,body:unknown){res.status(status).setHeader('Content-Type','application/json').setHeader('Cache-Control','no-store, private').json(body)}
function bearer(req:any){const v=String(req.headers?.authorization||'');return v.startsWith('Bearer ')?v.slice(7):''}
const noPermissions={view_questions:false,print_questions:false,download_files:false,copy_text:false,export_data:false}
const validKeys=new Set(Object.keys(noPermissions))
export default async function handler(req:any,res:any){
 if(req.method!=='POST')return json(res,405,{error:'Method not allowed.'})
 try{
  const ownerUid=process.env.OWNER_FIREBASE_UID;if(!ownerUid)return json(res,503,{error:'Owner access is not configured.'})
  const token=bearer(req);if(!token)return json(res,401,{error:'Sign in is required.'})
  const admin=authAdmin();const caller=await admin.verifyIdToken(token,true);if(caller.uid!==ownerUid)return json(res,403,{error:'Owner permission required.'})
  const database=db();const action=String(req.body?.action||'')
  if(action==='list'){const {data,error}=await database.from('approved_members').select('uid,email,approved,permissions,approved_at').eq('approved',true).neq('uid',ownerUid).order('approved_at',{ascending:false});if(error)throw error;return json(res,200,{members:data||[]})}
  if(action==='approve'){
   const email=String(req.body?.email||'').trim().toLowerCase();if(!/^\S+@\S+\.\S+$/.test(email))return json(res,400,{error:'Enter a valid email address.'})
   const target=await admin.getUserByEmail(email);if(target.uid===ownerUid)return json(res,400,{error:'The owner account is managed separately.'})
   const {error}=await database.from('approved_members').upsert({uid:target.uid,email:target.email||email,approved:true,approved_by:caller.uid,approved_at:new Date().toISOString(),permissions:{...noPermissions,view_questions:true}},{onConflict:'uid'});if(error)throw error
   return json(res,200,{ok:true})
  }
  const uid=String(req.body?.uid||'');if(!uid||uid===ownerUid)return json(res,400,{error:'Invalid member.'})
  if(action==='revoke'){const {error}=await database.from('approved_members').update({approved:false,permissions:noPermissions,revoked_at:new Date().toISOString(),revoked_by:caller.uid}).eq('uid',uid);if(error)throw error;return json(res,200,{ok:true})}
  if(action==='permissions'){
   const input=req.body?.permissions||{};const permissions:any={...noPermissions};for(const key of validKeys){if(typeof input[key]==='boolean')permissions[key]=input[key]}
   if(!permissions.view_questions)for(const key of ['print_questions','download_files','copy_text','export_data'])permissions[key]=false
   const {error}=await database.from('approved_members').update({permissions,updated_at:new Date().toISOString(),updated_by:caller.uid}).eq('uid',uid).eq('approved',true);if(error)throw error;return json(res,200,{ok:true})
  }
  return json(res,400,{error:'Unknown action.'})
 }catch(error){const message=error instanceof Error?error.message:'Request failed.';return json(res,/credentials are not configured/.test(message)?503:500,{error:message})}
}
