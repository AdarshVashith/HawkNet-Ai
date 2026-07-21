const PRODUCTION_BACKEND = 'https://hawknet-ai-backend.onrender.com'

function getApiBase(): string {
  // 1. Explicitly set via Vite env var (highest priority)
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '')
  }
  // 2. Running on Render static hosting → always use production backend
  if (typeof window !== 'undefined' && window.location.hostname.endsWith('onrender.com')) {
    return PRODUCTION_BACKEND
  }
  // 3. Local development — proxy through Vite dev server
  return ''
}


async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const base = getApiBase()
  const response = await fetch(`${base}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
  })

  const contentType = response.headers.get('content-type') || ''

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed (${response.status})`)
  }

  if (!contentType.includes('application/json')) {
    throw new Error(`API endpoint returned non-JSON response. Check backend connection at ${base}${path}`)
  }

  return response.json() as Promise<T>
}

export type HealthResponse = {
  status: string
  service: string
  version: string
  environment: string
}

export type ModuleResult = {
  request_id: string
  risk_level: string
  risk_score: number
  explanation: string
  model_version: string
}

export type AuditEvent = {
  event_id: string
  timestamp: string
  module_name: string
  confidence_score: number
  review_action: string
  risk_level?: string
  input_hash?: string
  output_hash?: string
}

export type ChainVerifyResult = {
  checked_count: number
  valid: boolean
  message: string
}

export type CurrencyScanResponse = {
  verdict: 'genuine' | 'counterfeit' | 'uncertain'
  confidence: number
  region_scores: {
    security_thread: number
    microprint: number
    serial_number: number
  }
  recommended_action: string
  model_version?: string
  audit_event_id?: string
  backend?: string
}

// ── Health ─────────────────────────────────────────────────────────
export function getHealth() {
  return request<HealthResponse>('/health')
}

// ── Scam Detection ─────────────────────────────────────────────────
export function analyzeScam(text: string, channel = 'dashboard') {
  return request<ModuleResult & { labels: string[]; signals: string[] }>(
    '/api/v1/scam-detection/analyze',
    {
      method: 'POST',
      body: JSON.stringify({ text, channel: channel.toLowerCase() }),
    },
  )
}

/** Score a single audio chunk from a live call */
export function scoreScamChunk(callId: string, chunkSequence: number, transcriptChunk: string) {
  return request<ModuleResult & { chunk_sequence: number; call_id: string }>(
    '/api/scam-detection/score',
    {
      method: 'POST',
      body: JSON.stringify({ call_id: callId, chunk_sequence: chunkSequence, transcript_chunk: transcriptChunk }),
    },
  )
}

// ── Counterfeit ────────────────────────────────────────────────────
export function analyzeCounterfeit(productName: string, brand: string, price: number, marketplace = 'dashboard') {
  return request<ModuleResult & { authenticity_score: number; red_flags: string[] }>(
    '/api/v1/counterfeit/analyze',
    {
      method: 'POST',
      body: JSON.stringify({
        product_name: productName,
        brand,
        price,
        marketplace,
      }),
    },
  )
}

/** Scan an uploaded banknote image for counterfeit security cues */
export async function scanCurrencyNote(file: File): Promise<CurrencyScanResponse> {
  const base = getApiBase()
  const formData = new FormData()
  formData.append('file', file)
  const response = await fetch(`${base}/api/counterfeit/scan`, {
    method: 'POST',
    body: formData,
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Currency scan failed (${response.status})`)
  }
  return response.json() as Promise<CurrencyScanResponse>
}

// ── Fraud Graph ────────────────────────────────────────────────────
export type GraphEntity = { id: string; type: string }
export type GraphEdge   = { source: string; target: string; relation: string }

export type SuspiciousCluster = {
  cluster_id: string
  rank: number
  suspicion_score: number
  member_accounts: string[]
  member_phones?: string[]
  member_devices?: string[]
  evidence?: string[]
  size?: number
}

export type ClusterListResponse = {
  clusters: SuspiciousCluster[]
  model_version: string
}

export function analyzeFraudGraph(
  entities: GraphEntity[] = [
    { id: 'acct-1', type: 'account' },
    { id: 'acct-2', type: 'account' },
    { id: 'device-1', type: 'device' },
  ],
  edges: GraphEdge[] = [
    { source: 'acct-1', target: 'device-1', relation: 'uses' },
    { source: 'acct-2', target: 'device-1', relation: 'uses' },
  ],
  seedEntityId = 'acct-1',
) {
  return request<ModuleResult & { cluster_size: number; suspicious_entities: string[] }>(
    '/api/v1/fraud-graph/analyze',
    {
      method: 'POST',
      body: JSON.stringify({ entities, edges, seed_entity_id: seedEntityId }),
    },
  )
}

/** List all known fraud clusters */
export function listFraudClusters() {
  return request<ClusterListResponse>('/api/fraud-graph/clusters')
}

/** Export Law Enforcement Intelligence Package for a fraud cluster */
export function exportFraudClusterPackage(clusterId: string) {
  return request<{
    package_type: string
    cluster_id: string
    generated_at: string
    confidence: number
    suspicion_score: number
    summary: string
    member_accounts: string[]
    member_phones: string[]
    member_devices: string[]
    evidence_trail: string[]
    recommended_actions: string[]
    audit_log_reference: string
  }>(`/api/fraud-graph/export/${clusterId}`, { method: 'POST' })
}

// ── Geospatial ─────────────────────────────────────────────────────
export function analyzeGeospatial(latitude: number, longitude: number, radiusKm = 5, category = 'general') {
  return request<ModuleResult & { hotspots_nearby: number; recommendations: string[]; region_label?: string }>(
    '/api/v1/geospatial/risk',
    {
      method: 'POST',
      body: JSON.stringify({ latitude, longitude, radius_km: radiusKm, category }),
    },
  )
}

export function getGeospatialHotspots() {
  return request<{ status: string; count: number; hotspots: Array<{ district: string; state: string; risk_score: number; priority_rank: number; latitude: number; longitude: number; primary_threat: string }> }>('/api/geospatial/hotspots')
}

// ── Citizen Shield ─────────────────────────────────────────────────
export type CitizenAssessResult = {
  verdict: 'likely_safe' | 'suspicious_verify_first' | 'high_risk_stop_now'
  confidence_score: number
  plain_explanation: string
  next_steps: string[]
  helpline: string
  report_url: string
  language: string
  matched_signals: string[]
  model_version: string
}

export function submitCitizenReport(category: string, description: string, location?: string, anonymous = true) {
  return request<{ report_id: string; status: string; message: string }>(
    '/api/v1/citizen-shield/report',
    {
      method: 'POST',
      body: JSON.stringify({ category, description, location, anonymous }),
    },
  )
}

export function assessCitizenRisk(description: string, answers: Record<string, boolean | string> = {}, language = 'en') {
  return request<CitizenAssessResult>(
    '/api/citizen-shield/assess',
    {
      method: 'POST',
      body: JSON.stringify({ description, answers, language }),
    },
  )
}

// ── Audit Log & Legal Chain ─────────────────────────────────────────
export async function listAuditEvents(skip = 0, limit = 20) {
  try {
    return await request<{ events: AuditEvent[]; total: number }>(`/api/v1/audit/?skip=${skip}&limit=${limit}`)
  } catch {
    return await request<{ events: AuditEvent[]; total: number }>(`/api/audit/?skip=${skip}&limit=${limit}`)
  }
}

export async function getAuditEvent(eventId: string) {
  try {
    return await request<AuditEvent & { input_data: unknown; output_data: unknown }>(`/api/v1/audit/${eventId}`)
  } catch {
    return await request<AuditEvent & { input_data: unknown; output_data: unknown }>(`/api/audit/${eventId}`)
  }
}

export async function verifyAuditChain() {
  try {
    return await request<ChainVerifyResult>('/api/v1/audit/chain/verify')
  } catch {
    return await request<ChainVerifyResult>('/api/audit/chain/verify')
  }
}

export async function reviewAuditEvent(eventId: string, reviewAction: 'confirm' | 'dismiss' | 'escalate', humanReviewer = 'Duty Officer') {
  try {
    return await request<{ status: string; event_id: string; review_action: string }>(
      `/api/v1/audit/${eventId}/review`,
      {
        method: 'PATCH',
        body: JSON.stringify({ review_action: reviewAction, human_reviewer: humanReviewer }),
      },
    )
  } catch {
    return await request<{ status: string; event_id: string; review_action: string }>(
      `/api/audit/${eventId}/review`,
      {
        method: 'PATCH',
        body: JSON.stringify({ review_action: reviewAction, human_reviewer: humanReviewer }),
      },
    )
  }
}

// ── Bot Webhook Simulator ──────────────────────────────────────────
export type BotWebhookResult = {
  sender: string
  platform: 'whatsapp' | 'telegram'
  reply_text: string
  verdict: string
  confidence_score: number
  helpline: string
  next_steps: string[]
}

export function postBotWebhook(message: string, platform: 'whatsapp' | 'telegram' = 'whatsapp', language = 'en', sender = '+919876543210') {
  return request<BotWebhookResult>('/api/citizen-shield/webhook/whatsapp', {
    method: 'POST',
    body: JSON.stringify({ message, platform, language, sender }),
  })
}

// ── Section 65B PDF Evidence Dossier ────────────────────────────────
export type Section65BDossier = {
  dossier_type: string
  certificate_title: string
  event_id: string
  timestamp_ist: string
  module_name: string
  confidence_score: number
  input_hash: string
  event_hash: string
  prev_hash: string
  chain_valid: boolean
  input_payload: unknown
  decision_output: unknown
  human_reviewer: string | null
  review_action: string | null
  statutory_certification_clause: string
  cryptographic_seal: string
}

export async function getSection65BDossier(eventId: string) {
  try {
    return await request<Section65BDossier>(`/api/v1/audit/${eventId}/dossier`)
  } catch {
    return await request<Section65BDossier>(`/api/audit/${eventId}/dossier`)
  }
}

// ── FIR Drafting Agent ─────────────────────────────────────────────────────

export type ComplainantInfo = {
  full_name: string
  contact_number: string
  address?: string
  id_proof_type?: string
  id_proof_number_last4?: string
}

export type SuggestedLegalSection = {
  act: string
  section: string
  plain_language_basis: string
  verified_by_officer: boolean
}

export type FIREvidenceItem = {
  event_id: string
  timestamp: string
  module_name: string
  input_reference: string
  model_version: string
  confidence_score: number
  decision_output: Record<string, unknown>
  human_reviewer: string | null
  review_action: string | null
}

export type FIRDraft = {
  draft_id: string
  created_at: string
  status: 'generated' | 'officer_reviewed' | 'filed' | 'rejected'
  complainant: ComplainantInfo
  evidence_items: FIREvidenceItem[]
  narrative: string
  suggested_sections: SuggestedLegalSection[]
  grounding_warnings: string[]
  total_estimated_loss?: number
  jurisdiction_police_station?: string
  jurisdiction_state?: string
  audit_chain_ref: string
  disclaimer: string
}

export type FIRDraftRequest = {
  complainant: ComplainantInfo
  evidence_event_ids: string[]
  incident_summary_by_officer?: string
  jurisdiction_police_station?: string
  jurisdiction_state?: string
}

export type FIRReviewUpdate = {
  status: FIRDraft['status']
  edited_narrative?: string
  verified_section_indexes: number[]
  officer_name: string
}

export function createFIRDraft(payload: FIRDraftRequest) {
  return request<FIRDraft>('/api/fir-agent/draft', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function reviewFIRDraft(draftId: string, update: FIRReviewUpdate) {
  return request<FIRDraft>(`/api/fir-agent/draft/${draftId}/review`, {
    method: 'PATCH',
    body: JSON.stringify(update),
  })
}

export function getFIRDraft(draftId: string) {
  return request<FIRDraft>(`/api/fir-agent/draft/${draftId}`)
}

export async function exportFIRDraft(draftId: string, filename: string): Promise<void> {
  const base = getApiBase()
  const response = await fetch(`${base}/api/fir-agent/draft/${draftId}/export`)
  if (!response.ok) throw new Error(`Export failed (${response.status})`)
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

