export type Credentials = {
  login: string
  password: string
}

export type InfoObject = {
  id: number
  title?: string | null
  content?: string | null
  source?: string | null
  author?: string | null
  url?: string | null
  doi?: string | null
  publication_title?: string | null
  publication_date_from_raw?: string | null
  publication_date_to_raw?: string | null
  tags?: string[]
  created_by?: number | null
  deletion_flag?: boolean
}

export type InfoObjectPage = {
  items: InfoObject[]
  total: number
  page: number
  size: number
  pages: number
}

export type SearchQuery = {
  id: number
  name: string
  title?: string | null
  text?: string | null
  author?: string | null
  source?: string | null
  publication_title?: string | null
  doi?: string | null
  tags?: string[]
  user_id: number
}

export type SearchQueryList = {
  items: SearchQuery[]
  total: number
}

export type SearchFilters = {
  title: string
  text: string
  author: string
  source: string
  publication_title: string
  doi: string
  tags: string
}

export type AgreementStatus = {
  accepted: boolean
  full_name?: string | null
  job_title?: string | null
  organization?: string | null
}

export type UserAdminRecord = {
  id: number
  login: string
  full_name?: string | null
  email?: string | null
  role: string
}

export type DeletionRequestRecord = {
  id: number
  info_object_id: number
  requested_by: number
  reason?: string | null
  replacement_info_object_id?: number | null
  status: string
  created_at: string
}

export type DeletionRequestStatus = {
  exists: boolean
  id?: number | null
  status?: string | null
  reason?: string | null
  replacement_info_object_id?: number | null
}