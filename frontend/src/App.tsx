import React, { useEffect, useMemo, useState } from 'react'
import { getCaptcha, verifyCaptcha, refreshCaptcha } from './captcha'
import { exportAllDatabases, exportKmsDatabases, exportUserDatabase } from './adminExport'
import type {
  AgreementStatus,
  Credentials,
  InfoObject,
  InfoObjectPage,
  SearchFilters,
  SearchQuery,
  SearchQueryList,
  UserAdminRecord,
  DeletionRequestRecord,
  DeletionRequestStatus,
} from './types'
import { apiFetch, apiFetchBlob, STORAGE_KEY, parseTags } from './api'

type MediaFile = {
  id: number
  original_name: string
  stored_name: string
  content_type?: string | null
  size_bytes: number
  checksum_sha256: string
  created_at: string
  uploaded_by?: number | null
}

const defaultFilters: SearchFilters = {
  title: '',
  text: '',
  author: '',
  source: '',
  publication_title: '',
  doi: '',
  tags: '',
}

const emptyCreateForm = {
  title: '',
  content: '',
  source: '',
  author: '',
  url: '',
  doi: '',
  publication_title: '',
  publication_date_from_raw: '',
  publication_date_to_raw: '',
  tags: '',
}

const emptyEditForm = {
  title: '',
  content: '',
  source: '',
  author: '',
  url: '',
  doi: '',
  publication_title: '',
  publication_date_from_raw: '',
  publication_date_to_raw: '',
  tags: '',
}
type CurrentUserInfo = {
  id: number
  login: string
  full_name?: string | null
  email?: string | null
  role: string
}

type PendingTagAction =
  | {
      type: 'replace'
      old_tag: string
      new_tag: string
      scope: 'mine' | 'all'
    }
  | {
      type: 'delete'
      tag: string
      scope: 'mine' | 'all'
    }

type TagSuggestInputProps = {
  label: string
  value: string
  credentials: Credentials | null
  onChange: (value: string) => void
  placeholder?: string
}

function TagSuggestInput({
  label,
  value,
  credentials,
  onChange,
  placeholder,
}: TagSuggestInputProps) {
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [open, setOpen] = useState(false)
  const wrapperRef = React.useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!wrapperRef.current) return
      if (!wrapperRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadSuggestions() {
      if (!credentials || !value.trim()) {
        setSuggestions([])
        return
      }

      try {
        const params = new URLSearchParams()
        params.set('q', value.trim())
        const result = await apiFetch<{ items: string[] }>(
          `/tags?${params.toString()}`,
          credentials
        )
        if (!cancelled) {
          setSuggestions(result.items.filter((item) => item !== value))
          setOpen(true)
        }
      } catch {
        if (!cancelled) {
          setSuggestions([])
        }
      }
    }

    void loadSuggestions()

    return () => {
      cancelled = true
    }
  }, [value, credentials])

  function chooseSuggestion(tag: string) {
    onChange(tag)
    setOpen(false)
  }

  return (
    <div ref={wrapperRef} style={{ position: 'relative' }}>
      <label>{label}</label>
      <input
        className="input"
        value={value}
        placeholder={placeholder}
        onChange={(e) => {
          onChange(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            setOpen(false)
            return
          }

          if (e.key === 'Enter' && suggestions.length > 0) {
            e.preventDefault()
            chooseSuggestion(suggestions[0])
          }
        }}
      />

      {open && suggestions.length > 0 && (
        <div className="suggestions">
          <div className="suggestions-header">
            <span>Подсказки</span>
            <button
              type="button"
              className="suggestions-close"
              onClick={() => setOpen(false)}
            >
              ×
            </button>
          </div>

          {suggestions.map((tag) => (
            <button
              key={tag}
              type="button"
              className="suggestion-item"
              onClick={() => chooseSuggestion(tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

type ViewState = {
  tab: string
  selectedInfoObject: InfoObject | null
  selectedFiles: MediaFile[]
}

export default function App() {
  const [credentials, setCredentials] = useState<Credentials | null>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })

  const [historyStack, setHistoryStack] = useState<ViewState[]>([
  {
      tab: 'dashboard',
      selectedInfoObject: null,
      selectedFiles: [],
    },
  ])

  const [agreement, setAgreement] = useState<AgreementStatus | null>(null)
  const [agreementForm, setAgreementForm] = useState({
    full_name: '',
    job_title: '',
    organization: '',
    accepted_rules: false,
    accepted_personal_data: false,
  })

  const [adminUsers, setAdminUsers] = useState<UserAdminRecord[]>([])
  const [adminCreateUserForm, setAdminCreateUserForm] = useState({
    login: '',
    password: '',
    full_name: '',
    email: '',
    role: 'ROLE_USER',
  })

  const [selectedDeletionRequest, setSelectedDeletionRequest] = useState<DeletionRequestStatus | null>(null)
  const [historyIndex, setHistoryIndex] = useState(0)
  const [deletionRequests, setDeletionRequests] = useState<DeletionRequestRecord[]>([])
  const [draftLogin, setDraftLogin] = useState(credentials?.login ?? 'user')
  const [draftPassword, setDraftPassword] = useState(credentials?.password ?? 'user123')
  const [activeTab, setActiveTab] = useState('dashboard')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const [filters, setFilters] = useState<SearchFilters>(defaultFilters)
  const [infoObjects, setInfoObjects] = useState<InfoObjectPage | null>(null)
  const [myInfoObjects, setMyInfoObjects] = useState<InfoObjectPage | null>(null)
  const [selectedInfoObject, setSelectedInfoObject] = useState<InfoObject | null>(null)
  const [selectedFiles, setSelectedFiles] = useState<MediaFile[]>([])
  const [searchQueries, setSearchQueries] = useState<SearchQueryList | null>(null)
  const [uploadFiles, setUploadFiles] = useState<FileList | null>(null)

  
  const [createForm, setCreateForm] = useState(emptyCreateForm)
  const [editForm, setEditForm] = useState(emptyEditForm)

  const [currentUser, setCurrentUser] = useState<CurrentUserInfo | null>(null)

  const [tagSearch, setTagSearch] = useState('')
  const [foundTags, setFoundTags] = useState<string[]>([])
  const [tagOld, setTagOld] = useState('')
  const [tagNew, setTagNew] = useState('')
  const [tagDeleteValue, setTagDeleteValue] = useState('')
  const [tagScope, setTagScope] = useState<'mine' | 'all'>('mine')
  const [pendingTagActions, setPendingTagActions] = useState<PendingTagAction[]>([])

  
  const isAuthenticated = !!credentials
  const hasFilters = useMemo(() => Object.values(filters).some(Boolean), [filters])
  const isAdmin = !!currentUser?.role?.includes('ROLE_ADMIN')
  const canGoBack = historyIndex > 0
  const canGoForward = historyIndex < historyStack.length - 1
  useEffect(() => {
    if (!credentials) return
    void loadDashboard()
  }, [credentials])

  async function loadDashboard() {
    if (!credentials) return
    setLoading(true)
    setError(null)
    try {
        const [allInfo, mine, queries, me, agreementStatus] = await Promise.all([
          apiFetch<InfoObjectPage>('/info-objects?page=0&size=20', credentials),
          apiFetch<InfoObjectPage>('/info-objects/my?page=0&size=20', credentials),
          apiFetch<SearchQueryList>('/search-queries/my', credentials),
          apiFetch<CurrentUserInfo>('/users/me', credentials),
          apiFetch<AgreementStatus>('/agreements/me', credentials),
        ])
        let usersList: UserAdminRecord[] = []
        if (me.role.includes('ROLE_ADMIN')) {
          usersList = await apiFetch<UserAdminRecord[]>('/users', credentials)
        }
        let deletionList: DeletionRequestRecord[] = []
        if (me.role.includes('ROLE_ADMIN')) {
          deletionList = await apiFetch<DeletionRequestRecord[]>('/deletion-requests', credentials)
        }
        setInfoObjects(allInfo)
        setMyInfoObjects(mine)
        setSearchQueries(queries)
        setCurrentUser(me)
        setAdminUsers(usersList)
        setAgreement(agreementStatus)
        setDeletionRequests(deletionList)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка загрузки данных')
    } finally {
      setLoading(false)
    }
  }

  async function loadFiles(infoObjectId: number) {
    if (!credentials) return
    const files = await apiFetch<MediaFile[]>(`/files/info-objects/${infoObjectId}`, credentials)
    setSelectedFiles(files)
  }

  function fillEditForm(item: InfoObject) {
    setEditForm({
      title: item.title ?? '',
      content: item.content ?? '',
      source: item.source ?? '',
      author: item.author ?? '',
      url: item.url ?? '',
      doi: item.doi ?? '',
      publication_title: item.publication_title ?? '',
      publication_date_from_raw: item.publication_date_from_raw ?? '',
      publication_date_to_raw: item.publication_date_to_raw ?? '',
      tags: (item.tags ?? []).join(', '),
    })
  }

  function fillCreateFormFromInfoObject(item: InfoObject) {
  setCreateForm({
    title: item.title ?? '',
    content: item.content ?? '',
    source: item.source ?? '',
    author: item.author ?? '',
    url: item.url ?? '',
    doi: item.doi ?? '',
    publication_title: item.publication_title ?? '',
    publication_date_from_raw: item.publication_date_from_raw ?? '',
    publication_date_to_raw: item.publication_date_to_raw ?? '',
    tags: (item.tags ?? []).join(', '),
  })
  }
  function applyViewState(view: ViewState) {
    setActiveTab(view.tab)
    setSelectedInfoObject(view.selectedInfoObject)
    setSelectedFiles(view.selectedFiles)
  }

  function pushViewState(view: ViewState) {
    setHistoryStack((prev) => {
      const cut = prev.slice(0, historyIndex + 1)
      const last = cut[cut.length - 1]

      const sameView =
        last &&
        last.tab === view.tab &&
        (last.selectedInfoObject?.id ?? null) === (view.selectedInfoObject?.id ?? null)

      if (sameView) {
        return prev
      }

      return [...cut, view]
    })

    setHistoryIndex((prev) => {
      const next = prev + 1
      return next
    })

    applyViewState(view)
  }

  function navigateToTab(tab: string) {
    pushViewState({
      tab,
      selectedInfoObject,
      selectedFiles,
    })
  }

  function goBackInApp() {
    if (!canGoBack) return

    const nextIndex = historyIndex - 1
    const view = historyStack[nextIndex]
    setHistoryIndex(nextIndex)
    applyViewState(view)
  }

  function goForwardInApp() {
    if (!canGoForward) return

    const nextIndex = historyIndex + 1
    const view = historyStack[nextIndex]
    setHistoryIndex(nextIndex)
    applyViewState(view)
  }
  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    const nextCreds = { login: draftLogin.trim(), password: draftPassword }
    setError(null)
    setLoading(true)
    try {
      await apiFetch<InfoObjectPage>('/info-objects?page=0&size=1', nextCreds)
      setCredentials(nextCreds)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(nextCreds))
      setHistoryStack([
        {
          tab: 'dashboard',
          selectedInfoObject: null,
          selectedFiles: [],
        },
      ])
      setHistoryIndex(0)
      setActiveTab('dashboard')
    } catch {
      setError('Не удалось войти. Проверьте логин и пароль.')
    } finally {
      setLoading(false)
    }
  }

  function handleLogout() {
    localStorage.removeItem(STORAGE_KEY)
    setCredentials(null)
    setInfoObjects(null)
    setMyInfoObjects(null)
    setSearchQueries(null)
    setSelectedInfoObject(null)
    setSelectedFiles([])
    setUploadFiles(null)
    setError(null)
    setHistoryStack([
      {
        tab: 'dashboard',
        selectedInfoObject: null,
        selectedFiles: [],
      },
    ])
    setHistoryIndex(0)
  }

  async function handleSearch() {
    if (!credentials) return
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (!value.trim()) return
        if (key === 'tags') {
          parseTags(value).forEach((tag) => params.append('tags', tag))
        } else {
          params.set(key, value.trim())
        }
      })
      params.set('page', '0')
      params.set('size', '20')
      const result = await apiFetch<InfoObjectPage>(`/info-objects/search?${params.toString()}`, credentials)
      setInfoObjects(result)
      pushViewState({
        tab: 'info-objects',
        selectedInfoObject,
        selectedFiles,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка поиска')
    } finally {
      setLoading(false)
    }
  }
  async function loadDeletionRequestStatus(infoObjectId: number) {
    if (!credentials) return
    const result = await apiFetch<DeletionRequestStatus>(
      `/deletion-requests/info-objects/${infoObjectId}/status`,
      credentials
    )
    setSelectedDeletionRequest(result)
  }
  async function handleOpenInfoObject(id: number) {
    if (!credentials) return
    setLoading(true)
    setError(null)
    try {
      const result = await apiFetch<InfoObject>(`/info-objects/${id}`, credentials)
      setSelectedInfoObject(result)
      fillEditForm(result)
      const files = await apiFetch<MediaFile[]>(`/files/info-objects/${id}`, credentials)
      setSelectedFiles(files)

      pushViewState({
        tab: 'detail',
        selectedInfoObject: result,
        selectedFiles: files,
      })
      await loadDeletionRequestStatus(id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось открыть ИО')
    } finally {
      setLoading(false)
    }
  }

  async function handleApproveDeletionRequest(requestId: number) {
    if (!credentials) return

    setLoading(true)
    setError(null)
    try {
      await apiFetch<void>(`/deletion-requests/${requestId}/approve-delete`, credentials, {
        method: 'POST',
      })
      await loadDashboard()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось удалить ИО по запросу')
    } finally {
      setLoading(false)
    }
  }

  async function handleAdminCreateUser(e: React.FormEvent) {
    e.preventDefault()
    if (!credentials) return

    setLoading(true)
    setError(null)
    try {
      await apiFetch<UserAdminRecord>('/users/admin-create', credentials, {
        method: 'POST',
        body: JSON.stringify({
          ...adminCreateUserForm,
          full_name: adminCreateUserForm.full_name || null,
          email: adminCreateUserForm.email || null,
        }),
      })

      setAdminCreateUserForm({
        login: '',
        password: '',
        full_name: '',
        email: '',
        role: 'ROLE_USER',
      })

      await loadDashboard()
      navigateToTab('users')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось создать пользователя')
    } finally {
      setLoading(false)
    }
  }
  async function handleCreateInfoObject(e: React.FormEvent) {
    e.preventDefault()
    if (!credentials) return
    setLoading(true)
    setError(null)
    try {
      const created = await apiFetch<InfoObject>('/info-objects', credentials, {
        method: 'POST',
        body: JSON.stringify({
          ...createForm,
          tags: parseTags(createForm.tags),
        }),
      })
      setSelectedInfoObject(created)
      fillEditForm(created)
      const files: MediaFile[] = []
      setSelectedFiles(files)

      pushViewState({
        tab: 'detail',
        selectedInfoObject: created,
        selectedFiles: files,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось создать ИО')
    } finally {
      setLoading(false)
    }
  }

  async function handleUpdateInfoObject(e: React.FormEvent) {
    e.preventDefault()
    if (!credentials || !selectedInfoObject) return
    setLoading(true)
    setError(null)
    try {
      const updated = await apiFetch<InfoObject>(`/info-objects/${selectedInfoObject.id}`, credentials, {
        method: 'PUT',
        body: JSON.stringify({
          ...editForm,
          tags: parseTags(editForm.tags),
        }),
      })
      setSelectedInfoObject(updated)
      fillEditForm(updated)
      await loadDashboard()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить изменения')
    } finally {
      setLoading(false)
    }
  }

  function handleCreateCopyFromSelected() {
    if (!selectedInfoObject) return
    fillCreateFormFromInfoObject(selectedInfoObject)
    pushViewState({
      tab: 'create',
      selectedInfoObject,
      selectedFiles,
    })
  }

 async function handleRequestDeletionInfoObject() {
  if (!credentials || !selectedInfoObject) return

  const reason = window.prompt('Укажите причину удаления', '') ?? ''
  const replacementRaw = window.prompt('Номер нового объекта (необязательно)', '') ?? ''

  setLoading(true)
  setError(null)
  try {
    await apiFetch(`/deletion-requests/info-objects/${selectedInfoObject.id}`, credentials, {
      method: 'POST',
      body: JSON.stringify({
        reason: reason.trim() || null,
        replacement_info_object_id: replacementRaw.trim() ? Number(replacementRaw.trim()) : null,
      }),
    })
    await loadDeletionRequestStatus(selectedInfoObject.id)
    alert('Запрос на удаление отправлен администратору.')
  } catch (e) {
    setError(e instanceof Error ? e.message : 'Не удалось отправить запрос на удаление')
  } finally {
    setLoading(false)
  }
}

  async function handleRestoreInfoObject() {
    if (!credentials || !selectedInfoObject) return
    setLoading(true)
    setError(null)
    try {
      const restored = await apiFetch<InfoObject>(`/info-objects/${selectedInfoObject.id}/restore`, credentials, {
        method: 'PATCH',
      })
      setSelectedInfoObject(restored)
      fillEditForm(restored)
      await loadDashboard()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось восстановить ИО')
    } finally {
      setLoading(false)
    }
  }

  async function handleUploadFiles(e: React.FormEvent) {
    e.preventDefault()
    if (!credentials || !selectedInfoObject || !uploadFiles?.length) return
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      Array.from(uploadFiles).forEach((file) => formData.append('files', file))
      await apiFetch<MediaFile[]>(`/files/info-objects/${selectedInfoObject.id}`, credentials, {
        method: 'POST',
        body: formData,
      })
      setUploadFiles(null)
      await loadFiles(selectedInfoObject.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось загрузить файлы')
    } finally {
      setLoading(false)
    }
  }

  async function handleDetachFile(fileId: number) {
    if (!credentials || !selectedInfoObject) return
    setLoading(true)
    setError(null)
    try {
      await apiFetch<void>(`/files/info-objects/${selectedInfoObject.id}/${fileId}`, credentials, {
        method: 'DELETE',
      })
      await loadFiles(selectedInfoObject.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось отвязать файл')
    } finally {
      setLoading(false)
    }
  }

  async function handleExportSelectedInfoObject() {
    if (!credentials || !selectedInfoObject) return

    setLoading(true)
    setError(null)
    try {
      const blob = await apiFetchBlob(
        `/info-objects/${selectedInfoObject.id}/export`,
        credentials
      )

      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `info_object_${selectedInfoObject.id}.zip`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось экспортировать объект')
    } finally {
      setLoading(false)
    }
  }

  async function handleSaveCurrentSearch() {
    if (!credentials) return
    const name = window.prompt('Название сохранённого запроса', 'Мой запрос')
    if (!name) return

    setLoading(true)
    setError(null)
    try {
      await apiFetch<SearchQuery>('/search-queries/', credentials, {
        method: 'POST',
        body: JSON.stringify({
          name,
          ...filters,
          tags: parseTags(filters.tags),
          tag_mode: 'AND',
        }),
      })
      await loadDashboard()
      pushViewState({
        tab: 'queries',
        selectedInfoObject,
        selectedFiles,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить запрос')
    } finally {
      setLoading(false)
    }
  }

  async function handleApplySavedQuery(query: SearchQuery) {
    setFilters({
      title: query.title ?? '',
      text: query.text ?? '',
      author: query.author ?? '',
      source: query.source ?? '',
      publication_title: query.publication_title ?? '',
      doi: query.doi ?? '',
      tags: (query.tags ?? []).join(', '),
    })
    await handleSearchFromQuery(query)
  }

  async function handleSearchFromQuery(query: SearchQuery) {
    if (!credentials) return
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (query.title) params.set('title', query.title)
      if (query.text) params.set('text', query.text)
      if (query.author) params.set('author', query.author)
      if (query.source) params.set('source', query.source)
      if (query.publication_title) params.set('publication_title', query.publication_title)
      if (query.doi) params.set('doi', query.doi)
      ;(query.tags ?? []).forEach((tag) => params.append('tags', tag))
      params.set('page', '0')
      params.set('size', '20')
      const result = await apiFetch<InfoObjectPage>(`/info-objects/search?${params.toString()}`, credentials)
      setInfoObjects(result)
      setActiveTab('info-objects')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось применить сохранённый запрос')
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteSavedQuery(id: number) {
    if (!credentials) return
    setLoading(true)
    setError(null)
    try {
      await apiFetch<void>(`/search-queries/${id}`, credentials, { method: 'DELETE' })
      await loadDashboard()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось удалить запрос')
    } finally {
      setLoading(false)
    }
  }

  async function handleSearchTags() {
    if (!credentials) return
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (tagSearch.trim()) {
        params.set('q', tagSearch.trim())
      }
      const result = await apiFetch<{ items: string[] }>(`/tags?${params.toString()}`, credentials)
      setFoundTags(result.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось выполнить поиск меток')
    } finally {
      setLoading(false)
    }
  }

  function handleStageReplaceTag() {
    if (!tagOld.trim() || !tagNew.trim()) {
      setError('Для операции 1→2 нужно указать обе метки.')
      return
    }

    setPendingTagActions((prev) => [
      ...prev,
      {
        type: 'replace',
        old_tag: tagOld.trim(),
        new_tag: tagNew.trim(),
        scope: tagScope,
      },
    ])

    setTagOld('')
    setTagNew('')
    setError(null)
  }

  function handleStageDeleteTag() {
    if (!tagDeleteValue.trim()) {
      setError('Для операции 1→∅ нужно указать метку.')
      return
    }

    setPendingTagActions((prev) => [
      ...prev,
      {
        type: 'delete',
        tag: tagDeleteValue.trim(),
        scope: tagScope,
      },
    ])

    setTagDeleteValue('')
    setError(null)
  }

  function handleUndoLastTagAction() {
    setPendingTagActions((prev) => prev.slice(0, -1))
  }

  function handleClearTagForm() {
    setTagSearch('')
    setFoundTags([])
    setTagOld('')
    setTagNew('')
    setTagDeleteValue('')
    setPendingTagActions([])
    setError(null)
  }

  async function handleSaveTagActions() {
    if (!credentials) return
    if (!pendingTagActions.length) {
      setError('Нет действий для сохранения.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      for (const action of pendingTagActions) {
        if (action.type === 'replace') {
          await apiFetch('/tags/replace', credentials, {
            method: 'POST',
            body: JSON.stringify({
              old_tag: action.old_tag,
              new_tag: action.new_tag,
              scope: action.scope,
            }),
          })
        } else {
          await apiFetch('/tags/delete', credentials, {
            method: 'POST',
            body: JSON.stringify({
              tag: action.tag,
              scope: action.scope,
            }),
          })
        }
      }

      setPendingTagActions([])
      await loadDashboard()
      await handleSearchTags()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить изменения меток')
    } finally {
      setLoading(false)
    }
  }

async function handleAcceptAgreement(e: React.FormEvent) {
  e.preventDefault()
  if (!credentials) return

  setLoading(true)
  setError(null)
  try {
    const result = await apiFetch<AgreementStatus>('/agreements/me', credentials, {
      method: 'POST',
      body: JSON.stringify(agreementForm),
    })
    setAgreement(result)
  } catch (e) {
    setError(e instanceof Error ? e.message : 'Не удалось сохранить согласие')
  } finally {
    setLoading(false)
  }
}

async function handleReplaceTag() {
  if (!credentials) return
  setLoading(true)
  setError(null)
  try {
    await apiFetch('/tags/replace', credentials, {
      method: 'POST',
      body: JSON.stringify({
        old_tag: tagOld,
        new_tag: tagNew,
        scope: tagScope,
      }),
    })
    await loadDashboard()
    await handleSearchTags()
  } catch (e) {
    setError(e instanceof Error ? e.message : 'Не удалось заменить метку')
  } finally {
    setLoading(false)
  }
}

  async function handleDeleteTag() {
    if (!credentials) return
    setLoading(true)
    setError(null)
    try {
      await apiFetch('/tags/delete', credentials, {
        method: 'POST',
        body: JSON.stringify({
          tag: tagDeleteValue,
          scope: tagScope,
        }),
      })
      await loadDashboard()
      await handleSearchTags()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось удалить метку')
    } finally {
      setLoading(false)
    }
  }

  async function handleExportAll() {
    if (!credentials) return
    setLoading(true)
    try {
      const blob = await exportAllDatabases(credentials)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `kms_full_export_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.zip`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка экспорта')
    } finally {
      setLoading(false)
    }
  }

  async function handleExportKms() {
    if (!credentials) return
    setLoading(true)
    try {
      const blob = await exportKmsDatabases(credentials)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `kms_export_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.zip`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка экспорта')
    } finally {
      setLoading(false)
    }
  }

  async function handleExportUser(login: string) {
    if (!credentials) return
    setLoading(true)
    try {
      const blob = await exportUserDatabase(credentials, login)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `kms_user_${login}_export_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.zip`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка экспорта')
    } finally {
      setLoading(false)
    }
  }

  if (!isAuthenticated) {
    const [captchaUrl, setCaptchaUrl] = useState<string>('')
    const [captchaCode, setCaptchaCode] = useState('')
    const [captchaError, setCaptchaError] = useState('')

    const loadCaptcha = async () => {
      const url = await getCaptcha()
      setCaptchaUrl(url)
    }

    useEffect(() => {
      loadCaptcha()
    }, [])

    const refreshCaptchaImage = async () => {
      const url = await refreshCaptcha()
      setCaptchaUrl(url)
      setCaptchaCode('')
      setCaptchaError('')
    }

    const handleLoginWithCaptcha = async (e: React.FormEvent) => {
      e.preventDefault()
      if (!captchaCode.trim()) {
        setCaptchaError('Введите код с картинки')
        return
      }

      const verification = await verifyCaptcha(captchaCode)
      if (!verification.ok) {
        setCaptchaError(verification.error || 'Неверный код')
        refreshCaptchaImage()
        return
      }

      const nextCreds = { login: draftLogin.trim(), password: draftPassword }
      setError(null)
      setLoading(true)
      try {
        await apiFetch<InfoObjectPage>('/info-objects?page=0&size=1', nextCreds)
        setCredentials(nextCreds)
        localStorage.setItem(STORAGE_KEY, JSON.stringify(nextCreds))
        setHistoryStack([
          {
            tab: 'dashboard',
            selectedInfoObject: null,
            selectedFiles: [],
          },
        ])
        setHistoryIndex(0)
        setActiveTab('dashboard')
      } catch {
        setError('Не удалось войти. Проверьте логин и пароль.')
        refreshCaptchaImage()
      } finally {
        setLoading(false)
      }
    }

    return (
      <div className="auth-shell">
        <div className="auth-card card">
          <h1 className="auth-title">Вход в СУЗ</h1>
          <p className="auth-subtitle">React-интерфейс поверх текущего backend</p>

          {error && <div className="error">{error}</div>}
          {captchaError && <div className="error">{captchaError}</div>}

          <form onSubmit={handleLoginWithCaptcha}>
            <div className="field">
              <label>Логин</label>
              <input
                className="input"
                value={draftLogin}
                onChange={(e) => setDraftLogin(e.target.value)}
              />
            </div>

            <div className="field">
              <label>Пароль</label>
              <input
                className="input"
                type="password"
                value={draftPassword}
                onChange={(e) => setDraftPassword(e.target.value)}
              />
            </div>

            <div className="field">
              <label>Код с картинки</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                {captchaUrl && <img src={captchaUrl} alt="Captcha" style={{ border: '1px solid #ccc', borderRadius: '8px' }} />}
                <button type="button" className="btn secondary" onClick={refreshCaptchaImage}>⟳</button>
              </div>
              <input
                className="input"
                type="text"
                value={captchaCode}
                onChange={(e) => setCaptchaCode(e.target.value)}
                placeholder="Введите код"
              />
            </div>

            <button className="btn" type="submit" disabled={loading}>
              {loading ? 'Входим...' : 'Войти'}
            </button>
          </form>

          <div className="muted" style={{ marginTop: 16 }}>
            Тестовые учётные записи: admin/admin123 и user/user123
          </div>
        </div>
      </div>
    )
  }
  if (credentials && agreement && !agreement.accepted) {
    return (
      <div className="auth-shell">
        <div className="auth-card card">
          <h1 className="auth-title">Принять правила</h1>
          <p className="auth-subtitle">Заполните форму и подтвердите оба согласия</p>

          {error && <div className="error">{error}</div>}

          <form onSubmit={handleAcceptAgreement}>
            <div className="field">
              <label>Пользователь (ФИО)</label>
              <input
                className="input"
                value={agreementForm.full_name}
                onChange={(e) => setAgreementForm((s) => ({ ...s, full_name: e.target.value }))}
              />
            </div>

            <div className="field">
              <label>Должность</label>
              <input
                className="input"
                value={agreementForm.job_title}
                onChange={(e) => setAgreementForm((s) => ({ ...s, job_title: e.target.value }))}
              />
            </div>

            <div className="field">
              <label>Организация</label>
              <input
                className="input"
                value={agreementForm.organization}
                onChange={(e) => setAgreementForm((s) => ({ ...s, organization: e.target.value }))}
              />
            </div>

            <div className="field">
              <label className="radio-line">
                <input
                  type="checkbox"
                  checked={agreementForm.accepted_rules}
                  onChange={(e) => setAgreementForm((s) => ({ ...s, accepted_rules: e.target.checked }))}
                />
                <span>Ознакомлен и принял правила работы</span>
              </label>
            </div>

            <div className="field">
              <label className="radio-line">
                <input
                  type="checkbox"
                  checked={agreementForm.accepted_personal_data}
                  onChange={(e) => setAgreementForm((s) => ({ ...s, accepted_personal_data: e.target.checked }))}
                />
                <span>Ознакомлен и согласен с использованием персональных данных</span>
              </label>
            </div>

            <div className="row">
              <button className="btn" type="submit" disabled={loading}>
                Перейти к работе
              </button>
              <button className="btn secondary" type="button" onClick={handleLogout}>
                Прекратить работу
              </button>
            </div>
          </form>
        </div>
      </div>
    )
  }
  return (
    <div className="page">
      <div className="container">
        <div className="card">
          <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h1 style={{ margin: 0 }}>Система управления знаниями</h1>
              <div className="muted">Текущий пользователь: {credentials.login}</div>
            </div>
            <div className="row">
              <div className="row">
                <button className="btn secondary" onClick={goBackInApp} disabled={!canGoBack}>
                  Назад
                </button>
                <button className="btn secondary" onClick={goForwardInApp} disabled={!canGoForward}>
                  Вперёд
                </button>
                <button className="btn secondary" onClick={() => void loadDashboard()}>
                  Обновить
                </button>
                <button className="btn secondary" onClick={handleLogout}>
                  Выйти
                </button>
              </div>
            </div>
          </div>
        </div>

        {error && <div className="error">{error}</div>}

        <div className="tabs">
          <button className={`tab ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => navigateToTab('dashboard')}>
            Главная
          </button>

          <button className={`tab ${activeTab === 'info-objects' ? 'active' : ''}`} onClick={() => navigateToTab('info-objects')}>
            Поиск ИО
          </button>

          <button className={`tab ${activeTab === 'create' ? 'active' : ''}`} onClick={() => navigateToTab('create')}>
            Создать ИО
          </button>

          <button className={`tab ${activeTab === 'queries' ? 'active' : ''}`} onClick={() => navigateToTab('queries')}>
            Мои запросы
          </button>

          <button className={`tab ${activeTab === 'tags' ? 'active' : ''}`} onClick={() => navigateToTab('tags')}>
            Метки
          </button>
          {isAdmin && (
            <button className={`tab ${activeTab === 'users' ? 'active' : ''}`} onClick={() => navigateToTab('users')}>
              Пользователи
            </button>
          )}

          {isAdmin && (
            <button className={`tab ${activeTab === 'delete-objects' ? 'active' : ''}`} onClick={() => navigateToTab('delete-objects')}>
              Удаление ИО
            </button>
          )}

          {isAdmin && (
            <button className={`tab ${activeTab === 'admin-export' ? 'active' : ''}`} onClick={() => navigateToTab('admin-export')}>
              Экспорт БД
            </button>
          )}

          <button className={`tab ${activeTab === 'detail' ? 'active' : ''}`} onClick={() => navigateToTab('detail')}>
            Карточка и файлы
          </button>
            </div>

        {activeTab === 'dashboard' && (
          <div className="grid-3">
            <div className="card">
              <h2>Все ИО</h2>
              <div className="kpi">{infoObjects?.total ?? 0}</div>
            </div>
            <div className="card">
              <h2>Мои ИО</h2>
              <div className="kpi">{myInfoObjects?.total ?? 0}</div>
            </div>
            <div className="card">
              <h2>Мои запросы</h2>
              <div className="kpi">{searchQueries?.total ?? 0}</div>
            </div>
          </div>
        )}

        {activeTab === 'info-objects' && (
          <div className="card">
            <h2 className="section-title">Поиск ИО</h2>
            <div className="grid-3">
              <input className="input" placeholder="Заголовок" value={filters.title} onChange={(e) => setFilters((s) => ({ ...s, title: e.target.value }))} />
              <input className="input" placeholder="Текст" value={filters.text} onChange={(e) => setFilters((s) => ({ ...s, text: e.target.value }))} />
              <input className="input" placeholder="Автор" value={filters.author} onChange={(e) => setFilters((s) => ({ ...s, author: e.target.value }))} />
              <input className="input" placeholder="Источник" value={filters.source} onChange={(e) => setFilters((s) => ({ ...s, source: e.target.value }))} />
              <input className="input" placeholder="Название публикации" value={filters.publication_title} onChange={(e) => setFilters((s) => ({ ...s, publication_title: e.target.value }))} />
              <input className="input" placeholder="DOI" value={filters.doi} onChange={(e) => setFilters((s) => ({ ...s, doi: e.target.value }))} />
            </div>

            <div style={{ marginTop: 16 }}>
              <input className="input" placeholder="Метки через запятую" value={filters.tags} onChange={(e) => setFilters((s) => ({ ...s, tags: e.target.value }))} />
            </div>

            <div className="row" style={{ marginTop: 16 }}>
              <button className="btn" onClick={() => void handleSearch()} disabled={loading}>Искать</button>
              <button className="btn secondary" onClick={() => setFilters(defaultFilters)}>Сбросить</button>
              <button className="btn secondary" onClick={() => void handleSaveCurrentSearch()} disabled={!hasFilters || loading}>Сохранить запрос</button>
            </div>

            <div style={{ marginTop: 24 }}>
              {(infoObjects?.items ?? []).map((item) => (
                <div className="card" key={item.id}>
                  <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <h3 className="object-card-title">{item.title || `ИО #${item.id}`}</h3>
                      <div className="muted">Автор: {item.author || '—'}</div>
                      <div className="muted">Источник: {item.source || '—'}</div>
                      <div style={{ marginTop: 8 }}>
                        {(item.tags ?? []).map((tag) => (
                          <span key={tag} className="badge" style={{ marginRight: 8 }}>{tag}</span>
                        ))}
                      </div>
                    </div>
                    <button className="btn secondary" onClick={() => void handleOpenInfoObject(item.id)}>Открыть</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'create' && (
          <div className="card">
            <h2 className="section-title">Создание ИО</h2>
            <div className="muted" style={{ marginBottom: 16 }}>
              Эту форму можно использовать как для нового объекта, так и для сохранения копии уже существующего объекта.
            </div>
            <form onSubmit={handleCreateInfoObject}>
              <div className="grid-2">
                <input className="input" placeholder="Заголовок" value={createForm.title} onChange={(e) => setCreateForm((s) => ({ ...s, title: e.target.value }))} />
                <input className="input" placeholder="Автор" value={createForm.author} onChange={(e) => setCreateForm((s) => ({ ...s, author: e.target.value }))} />
              </div>

              <div style={{ marginTop: 16 }}>
                <textarea className="textarea" placeholder="Текст" value={createForm.content} onChange={(e) => setCreateForm((s) => ({ ...s, content: e.target.value }))} />
              </div>

              <div className="grid-2" style={{ marginTop: 16 }}>
                <input className="input" placeholder="Источник" value={createForm.source} onChange={(e) => setCreateForm((s) => ({ ...s, source: e.target.value }))} />
                <input className="input" placeholder="URL" value={createForm.url} onChange={(e) => setCreateForm((s) => ({ ...s, url: e.target.value }))} />
                <input className="input" placeholder="DOI" value={createForm.doi} onChange={(e) => setCreateForm((s) => ({ ...s, doi: e.target.value }))} />
                <input className="input" placeholder="Название публикации" value={createForm.publication_title} onChange={(e) => setCreateForm((s) => ({ ...s, publication_title: e.target.value }))} />
                <input className="input" placeholder="Дата от" value={createForm.publication_date_from_raw} onChange={(e) => setCreateForm((s) => ({ ...s, publication_date_from_raw: e.target.value }))} />
                <input className="input" placeholder="Дата до" value={createForm.publication_date_to_raw} onChange={(e) => setCreateForm((s) => ({ ...s, publication_date_to_raw: e.target.value }))} />
              </div>

              <div style={{ marginTop: 16 }}>
                <input className="input" placeholder="Метки через запятую" value={createForm.tags} onChange={(e) => setCreateForm((s) => ({ ...s, tags: e.target.value }))} />
              </div>

              <div style={{ marginTop: 16 }}>
                <button className="btn" type="submit" disabled={loading}>Создать</button>
              </div>
            </form>
          </div>
        )}

        {activeTab === 'queries' && (
          <div className="card">
            <h2 className="section-title">Мои поисковые запросы</h2>
            {(searchQueries?.items ?? []).map((item) => (
              <div className="card" key={item.id}>
                <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h3 className="object-card-title">{item.name}</h3>
                    <div className="muted">
                      {[item.title, item.text, item.author, item.source, item.publication_title, item.doi]
                        .filter(Boolean)
                        .join(' | ') || 'Без параметров'}
                    </div>
                    {!!item.tags?.length && (
                      <div style={{ marginTop: 8 }}>
                        {item.tags.map((tag) => (
                          <span key={tag} className="badge" style={{ marginRight: 8 }}>{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="row">
                    <button className="btn secondary" onClick={() => void handleApplySavedQuery(item)}>Применить</button>
                    <button className="btn danger" onClick={() => void handleDeleteSavedQuery(item.id)}>Удалить</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        {activeTab === 'tags' && (
          <div className="card">
            <h2 className="section-title">Изменить метки</h2>

            <div className="grid-2">
              <div>
                <label>Найти метку</label>
                <input
                  className="input"
                  value={tagSearch}
                  onChange={(e) => setTagSearch(e.target.value)}
                  placeholder="Введите часть названия метки"
                />
                <div style={{ marginTop: 12 }}>
                  <button className="btn" type="button" onClick={() => void handleSearchTags()} disabled={loading}>
                    Найти
                  </button>
                </div>

                <div style={{ marginTop: 16 }}>
                  {foundTags.map((tag) => (
                    <div key={tag} className="badge" style={{ marginRight: 8, marginBottom: 8 }}>
                      {tag}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                {isAdmin ? (
                  <>
                    <label>Область изменения</label>
                    <div className="row">
                      <label className="radio-line">
                        <input
                          type="radio"
                          checked={tagScope === 'mine'}
                          onChange={() => setTagScope('mine')}
                        />
                        <span>Для моих сведений</span>
                      </label>

                      <label className="radio-line">
                        <input
                          type="radio"
                          checked={tagScope === 'all'}
                          onChange={() => setTagScope('all')}
                        />
                        <span>Для всех сведений</span>
                      </label>
                    </div>
                  </>
                ) : (
                  <>
                    <label>Область изменения</label>
                    <div className="muted">Для моих сведений</div>
                  </>
                )}
              </div>
            </div>

            <div className="grid-2" style={{ marginTop: 24 }}>
              <div className="card">
                <h3>1 → 2</h3>
                <TagSuggestInput
                  label="Метка 1"
                  value={tagOld}
                  credentials={credentials}
                  onChange={setTagOld}
                  placeholder="Введите метку"
                />
                <div style={{ height: 12 }} />
                <TagSuggestInput
                  label="Заменить на метку 2"
                  value={tagNew}
                  credentials={credentials}
                  onChange={setTagNew}
                  placeholder="Введите новую метку"
                />
                <div style={{ marginTop: 12 }}>
                  <button className="btn" type="button" onClick={handleStageReplaceTag} disabled={loading}>
                    Добавить действие 1→2
                  </button>
                </div>
              </div>

              <div className="card">
                <h3>1 → ∅</h3>
                <TagSuggestInput
                  label="Метка для удаления"
                  value={tagDeleteValue}
                  credentials={credentials}
                  onChange={setTagDeleteValue}
                  placeholder="Введите метку"
                />
                <div style={{ marginTop: 12 }}>
                  <button className="btn danger" type="button" onClick={handleStageDeleteTag} disabled={loading}>
                    Добавить действие 1→∅
                  </button>
                </div>
              </div>
            </div>

            <div className="card" style={{ marginTop: 24 }}>
              <h3>Очередь действий</h3>

              {pendingTagActions.length ? (
                <ul style={{ paddingLeft: 20 }}>
                  {pendingTagActions.map((action, index) => (
                    <li key={index} style={{ marginBottom: 8 }}>
                      {action.type === 'replace'
                        ? `1→2: ${action.old_tag} → ${action.new_tag} (${action.scope === 'all' ? 'для всех' : 'для моих'})`
                        : `1→∅: ${action.tag} (${action.scope === 'all' ? 'для всех' : 'для моих'})`}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="muted">Действий пока нет</div>
              )}

              <div className="row" style={{ marginTop: 16 }}>
                <button className="btn secondary" type="button" onClick={handleUndoLastTagAction} disabled={!pendingTagActions.length || loading}>
                  Отменить последнее действие
                </button>
                <button className="btn" type="button" onClick={() => void handleSaveTagActions()} disabled={!pendingTagActions.length || loading}>
                  Сохранить результаты
                </button>
                <button className="btn secondary" type="button" onClick={handleClearTagForm} disabled={loading}>
                  Очистить форму
                </button>
                <button className="btn secondary" type="button" onClick={handleLogout}>
                  Выйти из программы
                </button>
              </div>
            </div>
          </div>
        )}
        {activeTab === 'users' && isAdmin && (
          <div className="grid-2">
            <div className="card">
              <h2 className="section-title">Регистрация пользователя администратором</h2>

              <form onSubmit={handleAdminCreateUser}>
                <div className="field">
                  <label>Логин</label>
                  <input
                    className="input"
                    value={adminCreateUserForm.login}
                    onChange={(e) => setAdminCreateUserForm((s) => ({ ...s, login: e.target.value }))}
                  />
                </div>

                <div className="field">
                  <label>Пароль</label>
                  <input
                    className="input"
                    type="password"
                    value={adminCreateUserForm.password}
                    onChange={(e) => setAdminCreateUserForm((s) => ({ ...s, password: e.target.value }))}
                  />
                </div>

                <div className="field">
                  <label>ФИО</label>
                  <input
                    className="input"
                    value={adminCreateUserForm.full_name}
                    onChange={(e) => setAdminCreateUserForm((s) => ({ ...s, full_name: e.target.value }))}
                  />
                </div>

                <div className="field">
                  <label>Email</label>
                  <input
                    className="input"
                    value={adminCreateUserForm.email}
                    onChange={(e) => setAdminCreateUserForm((s) => ({ ...s, email: e.target.value }))}
                  />
                </div>

                <div className="field">
                  <label>Роль</label>
                  <select
                    className="input"
                    value={adminCreateUserForm.role}
                    onChange={(e) => setAdminCreateUserForm((s) => ({ ...s, role: e.target.value }))}
                  >
                    <option value="ROLE_USER">ROLE_USER</option>
                    <option value="ROLE_ADMIN">ROLE_ADMIN</option>
                  </select>
                </div>

                <button className="btn" type="submit" disabled={loading}>
                  Зарегистрировать пользователя
                </button>
              </form>
            </div>

            <div className="card">
              <h2 className="section-title">Список пользователей</h2>

              {adminUsers.length ? (
                <table className="table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Логин</th>
                      <th>ФИО</th>
                      <th>Email</th>
                      <th>Роль</th>
                    </tr>
                  </thead>
                  <tbody>
                    {adminUsers.map((user) => (
                      <tr key={user.id}>
                        <td>{user.id}</td>
                        <td>{user.login}</td>
                        <td>{user.full_name || '—'}</td>
                        <td>{user.email || '—'}</td>
                        <td>{user.role}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="muted">Пользователи не загружены.</div>
              )}
            </div>
          </div>
        )}
        {activeTab === 'delete-objects' && isAdmin && (
          <div className="card">
            <h2 className="section-title">Запросы на удаление ИО</h2>

            {deletionRequests.length ? (
              <table className="table">
                <thead>
                  <tr>
                    <th>ID запроса</th>
                    <th>ID ИО</th>
                    <th>Пользователь</th>
                    <th>Причина</th>
                    <th>Новый объект</th>
                    <th>Статус</th>
                    <th>Действие</th>
                  </tr>
                </thead>
                <tbody>
                  {deletionRequests.map((item) => (
                    <tr key={item.id}>
                      <td>{item.id}</td>
                      <td>{item.info_object_id}</td>
                      <td>{item.requested_by}</td>
                      <td>{item.reason || '—'}</td>
                      <td>{item.replacement_info_object_id || '—'}</td>
                      <td>{item.status}</td>
                      <td>
                        {item.status === 'pending' ? (
                          <button
                            className="btn danger"
                            type="button"
                            onClick={() => void handleApproveDeletionRequest(item.id)}
                            disabled={loading}
                          >
                            Удалить ИО
                          </button>
                        ) : (
                          <span className="muted">Обработано</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="muted">Запросов на удаление пока нет.</div>
            )}
          </div>
        )}
        {activeTab === 'admin-export' && isAdmin && (
          <div className="card">
            <h2 className="section-title">Экспорт баз данных</h2>
            <div className="grid-2" style={{ marginBottom: 24 }}>
              <div className="card">
                <h3>Экспорт всех БД</h3>
                <p className="muted">Полный дамп всех таблиц</p>
                <button className="btn" onClick={handleExportAll} disabled={loading}>Скачать ZIP</button>
              </div>
              <div className="card">
                <h3>Экспорт БД СУЗ</h3>
                <p className="muted">Только информационные объекты и метки</p>
                <button className="btn" onClick={handleExportKms} disabled={loading}>Скачать ZIP</button>
              </div>
            </div>
            <div className="card">
              <h3>Экспорт БД пользователя</h3>
              <p className="muted">Введите логин пользователя</p>
              <div className="row">
                <input
                  id="export-user-login"
                  type="text"
                  placeholder="Логин пользователя"
                  style={{ flex: 1 }}
                />
                <button className="btn" onClick={() => {
                  const loginInput = document.getElementById('export-user-login') as HTMLInputElement
                  if (loginInput.value.trim()) {
                    handleExportUser(loginInput.value.trim())
                  } else {
                    setError('Введите логин пользователя')
                  }
                }} disabled={loading}>Экспортировать</button>
              </div>
            </div>
          </div>
        )}
        {activeTab === 'detail' && (
          <>
            <div className="card">
              <h2 className="section-title">Карточка ИО</h2>
              {selectedInfoObject ? (
                <>
                  <h3>{selectedInfoObject.title || `ИО #${selectedInfoObject.id}`}</h3>
                  <div className="grid-2">
                    <div><strong>Автор:</strong> {selectedInfoObject.author || '—'}</div>
                    <div><strong>Источник:</strong> {selectedInfoObject.source || '—'}</div>
                    <div><strong>DOI:</strong> {selectedInfoObject.doi || '—'}</div>
                    <div><strong>Публикация:</strong> {selectedInfoObject.publication_title || '—'}</div>
                    <div><strong>Дата от:</strong> {selectedInfoObject.publication_date_from_raw || '—'}</div>
                    <div><strong>Дата до:</strong> {selectedInfoObject.publication_date_to_raw || '—'}</div>
                    <div><strong>Создал:</strong> {selectedInfoObject.created_by || '—'}</div>
                    <div>
                    <strong>Статус:</strong>{' '}
                      {selectedInfoObject.deletion_flag ? 'Помечен на удаление' : 'Активен'}
                    </div>
                    <div className="row" style={{ marginTop: 16 }}>
                      <button
                        className="btn secondary"
                        type="button"
                        onClick={() => void handleExportSelectedInfoObject()}
                        disabled={loading}
                      >
                        Экспортировать объект
                      </button>
                    </div>
                  </div>

                  <div style={{ marginTop: 16 }}>
                    <strong>Текст:</strong>
                    <div className="card" style={{ background: '#f8fafc' }}>
                      {selectedInfoObject.content || '—'}
                    </div>
                  </div>

                  <div style={{ marginTop: 16 }}>
                    {(selectedInfoObject.tags ?? []).map((tag) => (
                      <span key={tag} className="badge" style={{ marginRight: 8 }}>{tag}</span>
                    ))}
                  </div>
                </>
              ) : (
                <div className="muted">Выберите ИО из списка.</div>
              )}
            </div>

            {selectedInfoObject && (
              <div className="grid-2">
                <div className="card">
                  <div className="card">
                    <h2 className="section-title">Действия с объектом</h2>

                    <div className="row">
                      <button
                        className="btn"
                        type="button"
                        onClick={handleCreateCopyFromSelected}
                        disabled={loading}
                      >
                        Создать копию для редактирования
                      </button>

                      {selectedInfoObject.deletion_flag ? (
                        <button className="btn secondary" type="button" disabled>
                          Помечен на удаление
                        </button>
                      ) : (
                        <button
                          className="btn danger"
                          type="button"
                          onClick={() => void handleRequestDeletionInfoObject()}
                          disabled={loading}
                        >
                          Запросить удаление
                        </button>
                      )}

                      <button
                        className="btn secondary"
                        type="button"
                        onClick={() => void handleRestoreInfoObject()}
                        disabled={loading}
                      >
                        Восстановить
                      </button>
                    </div>

                    <div className="muted" style={{ marginTop: 16 }}>
                      По ТЗ изменение ИО должно происходить через создание его копии и дальнейшее редактирование копии.
                    </div>
                  </div>
                </div>

                <div className="card">
                  <h2 className="section-title">Файлы</h2>
                  <form onSubmit={handleUploadFiles}>
                    <input
                      className="input"
                      type="file"
                      multiple
                      onChange={(e) => setUploadFiles(e.target.files)}
                    />
                    <div style={{ marginTop: 16 }}>
                      <button className="btn" type="submit" disabled={loading || !uploadFiles?.length}>Загрузить</button>
                    </div>
                  </form>

                  <div style={{ marginTop: 20 }}>
                    {selectedFiles.length ? (
                      <table className="table">
                        <thead>
                          <tr>
                            <th>ID</th>
                            <th>Имя</th>
                            <th>Размер</th>
                            <th>Действия</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedFiles.map((file) => (
                            <tr key={file.id}>
                              <td>{file.id}</td>
                              <td>{file.original_name}</td>
                              <td>{file.size_bytes} байт</td>
                              <td>
                                <div className="row">
                                  <a className="btn secondary" href={`/api/files/info-objects/${selectedInfoObject.id}/${file.id}/download`}>
                                    Скачать
                                  </a>
                                  <button className="btn danger" type="button" onClick={() => void handleDetachFile(file.id)}>
                                    Отвязать
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div className="muted">Файлы пока не прикреплены.</div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}