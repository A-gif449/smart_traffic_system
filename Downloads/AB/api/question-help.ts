import { cert, getApps, initializeApp } from 'firebase-admin/app'
import { getAuth } from 'firebase-admin/auth'
import { createClient } from '@supabase/supabase-js'

async function requireApproved(req:any) {
  const projectId=process.env.FIREBASE_PROJECT_ID||process.env.VITE_FIREBASE_PROJECT_ID
  const clientEmail=process.env.FIREBASE_CLIENT_EMAIL
  const privateKey=process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g,'\n')
  const ownerUid=process.env.OWNER_FIREBASE_UID
  const url=process.env.SUPABASE_URL||process.env.VITE_SUPABASE_URL
  const serviceKey=process.env.SUPABASE_SERVICE_ROLE_KEY
  if(!projectId||!clientEmail||!privateKey||!ownerUid||!url||!serviceKey) throw new Error('Private access is not configured on the server.')
  if(!getApps().length) initializeApp({credential:cert({projectId,clientEmail,privateKey})})
  const header=String(req.headers?.authorization||'')
  if(!header.startsWith('Bearer ')) throw new Error('Sign in is required.')
  const identity=await getAuth().verifyIdToken(header.slice(7),true)
  if(identity.uid===ownerUid) return
  const db=createClient(url,serviceKey,{auth:{persistSession:false,autoRefreshToken:false}})
  const {data,error}=await db.from('approved_members').select('approved,permissions').eq('uid',identity.uid).maybeSingle()
  if(error||!data?.approved||!data?.permissions?.view_questions) throw new Error('Owner approval is required.')
}

export default async function handler(req:any,res:any) {
  res.setHeader('Cache-Control','no-store, private')
  if(req.method!=='POST') return res.status(405).json({error:'Method not allowed.'})
  try { await requireApproved(req) } catch(error) { return res.status(403).json({error:error instanceof Error?error.message:'Access denied.'}) }
  const question=req.body?.question
  if(!question?.id) return res.status(400).json({error:'Question details are required.'})
  const topic=String(question.topic||question.subject||'GATE CSE').slice(0,100)
  return res.status(200).json({
    configured:false,
    answer:null,
    hint:`Open the original GateOverflow discussion and identify exactly what is being asked. List the constraints before choosing a method for ${topic}.`,
    approach:`Use the source discussion for the full statement, then solve it independently. Record the key concept, assumptions, and a short verification of your result.`,
    alternatives:['Try a direct method first, then check whether a boundary case simplifies it.','After solving, verify each assumption against the original statement.'],
    answer_check:'The answer key is intentionally not stored in this app. Verify your result against the original source discussion.',
    trap:'Do not infer missing values, options, or assumptions from the topic title alone.',
    note:'Question text and answer keys are not stored here. Open the original GateOverflow discussion for the full question.'
  })
}
