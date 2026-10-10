
import { cert, getApps, initializeApp } from 'firebase-admin/app'
import { getAuth } from 'firebase-admin/auth'
import { createClient } from '@supabase/supabase-js'

function adminAuth() {
  const projectId =
    process.env.FIREBASE_PROJECT_ID ||
    process.env.VITE_FIREBASE_PROJECT_ID

  const clientEmail = process.env.FIREBASE_CLIENT_EMAIL
  const privateKey = process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, '\n')

  if (!projectId || !clientEmail || !privateKey) {
    throw new Error('Firebase Admin credentials are not configured.')
  }

  if (!getApps().length) {
    initializeApp({
      credential: cert({ projectId, clientEmail, privateKey })
    })
  }

  return getAuth()
}

function db() {
  const url =
    process.env.SUPABASE_URL ||
    process.env.VITE_SUPABASE_URL

  const key = process.env.SUPABASE_SERVICE_ROLE_KEY

  if (!url || !key) {
    throw new Error('Supabase server credentials are not configured.')
  }

  return createClient(url, key, {
    auth: {
      persistSession: false,
      autoRefreshToken: false
    }
  })
}

function json(res: any, status: number, body: unknown) {
  return res
    .status(status)
    .setHeader('Content-Type', 'application/json')
    .setHeader('Cache-Control', 'no-store, private')
    .json(body)
}

function bearer(req: any) {
  const value = String(req.headers?.authorization || '')
  return value.startsWith('Bearer ') ? value.slice(7) : ''
}

const allPermissions = {
  view_questions: true,
  print_questions: true,
  download_files: true,
  copy_text: true,
  export_data: true
}

const noPermissions = {
  view_questions: false,
  print_questions: false,
  download_files: false,
  copy_text: false,
  export_data: false
}

function logSupabaseError(stage: string, error: any) {
  // Log diagnostic fields only. Never log credentials or authentication tokens.
  console.error(`[api/access] ${stage}`, {
    code: error?.code,
    message: error?.message,
    details: error?.details,
    hint: error?.hint
  })
}

export default async function handler(req: any, res: any) {
  if (req.method !== 'GET') {
    return json(res, 405, { error: 'Method not allowed.' })
  }

  try {
    const ownerUid = process.env.OWNER_FIREBASE_UID

    if (!ownerUid) {
      return json(res, 503, {
        error: 'Owner access is not configured. Set OWNER_FIREBASE_UID on the server.'
      })
    }

    const token = bearer(req)

    if (!token) {
      return json(res, 401, { error: 'Sign in is required.' })
    }

    const user = await adminAuth().verifyIdToken(token, true)

    if (user.uid === ownerUid) {
      const ownerDb = db()

      const {
        data: existingOwner,
        error: lookupError
      } = await ownerDb
        .from('approved_members')
        .select('uid')
        .eq('uid', user.uid)
        .maybeSingle()

      if (lookupError) {
        logSupabaseError('Owner access lookup failed', lookupError)

        return json(res, 503, {
          error: 'Owner access record could not be checked. Check local server logs.'
        })
      }

      const { error: ownerError } = await ownerDb
        .from('approved_members')
        .upsert(
          {
            uid: user.uid,
            email: String(user.email || 'owner@private.local'),
            approved: true,
            approved_by: user.uid,
            approved_at: new Date().toISOString(),
            permissions: allPermissions
          },
          { onConflict: 'uid' }
        )

      if (ownerError) {
        logSupabaseError('Owner access initialization failed', ownerError)

        return json(res, 503, {
          error: 'Owner access record could not be initialized. Check local server logs.'
        })
      }

      return json(res, 200, {
        approved: true,
        isOwner: true,
        permissions: allPermissions,
        ownerInitialized: !existingOwner
      })
    }

    const {
      data,
      error
    } = await db()
      .from('approved_members')
      .select('approved,permissions')
      .eq('uid', user.uid)
      .maybeSingle()

    if (error) {
      logSupabaseError('Member approval lookup failed', error)

      return json(res, 503, {
        error: 'Could not verify approval. Please try again later.'
      })
    }

    const permissions = {
      ...noPermissions,
      ...(data?.permissions || {})
    }

    const approved = Boolean(
      data?.approved && permissions.view_questions
    )

    return json(res, 200, {
      approved,
      isOwner: false,
      permissions: approved ? permissions : noPermissions
    })
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : 'Access verification failed.'

    const status =
      /credentials are not configured/i.test(message) ? 503 : 401

    // Avoid logging the token or credential values.
    console.error('[api/access] Request failed:', message)

    return json(res, status, {
      error: message
    })
  }
}
