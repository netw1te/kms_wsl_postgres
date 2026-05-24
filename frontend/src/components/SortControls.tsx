import React from 'react'
import { SortField, SortDirection } from '../types'

interface SortControlsProps {
  sortConfig: {
    field: SortField
    direction: SortDirection
  }
  onSortChange: (field: SortField) => void
  onDirectionChange: (direction: SortDirection) => void
  disabled?: boolean
}

const SORT_FIELDS: { value: SortField; label: string }[] = [
  { value: 'id', label: 'ID' },
  { value: 'title', label: 'Заголовку' },
  { value: 'author', label: 'Автору' },
  { value: 'source', label: 'Источнику' },
  { value: 'publication_title', label: 'Названию публикации' },
  { value: 'created_at', label: 'Дате создания' },
  { value: 'publication_date', label: 'Дате публикации' },
]

export function SortControls({
  sortConfig,
  onSortChange,
  onDirectionChange,
  disabled
}: SortControlsProps) {
  return (
    <div className="sort-controls">
      <div className="sort-field">
        <label>Сортировать по:</label>
        <select
          value={sortConfig.field}
          onChange={(e) => onSortChange(e.target.value as SortField)}
          disabled={disabled}
          className="input"
        >
          {SORT_FIELDS.map((field) => (
            <option key={field.value} value={field.value}>
              {field.label}
            </option>
          ))}
        </select>
      </div>

      <div className="sort-direction">
        <label>Направление:</label>
        <div className="direction-buttons">
          <button
            type="button"
            className={`direction-btn ${sortConfig.direction === 'asc' ? 'active' : ''}`}
            onClick={() => onDirectionChange('asc')}
            disabled={disabled}
          >
            ↑ По возрастанию
          </button>
          <button
            type="button"
            className={`direction-btn ${sortConfig.direction === 'desc' ? 'active' : ''}`}
            onClick={() => onDirectionChange('desc')}
            disabled={disabled}
          >
            ↓ По убыванию
          </button>
        </div>
      </div>
    </div>
  )
}