import React, { useState } from 'react'
import {
  ComplexQueryGroup,
  ComplexQueryCondition,
  ConditionField,
  ConditionOperator,
  createEmptyCondition,
} from '../types/complexQuery'

interface ComplexQueryBuilderProps {
  query: ComplexQueryGroup
  onChange: (query: ComplexQueryGroup) => void
  onClose: () => void
}

const FIELD_OPTIONS: { value: ConditionField; label: string }[] = [
  { value: 'title', label: 'Заголовок' },
  { value: 'content', label: 'Текст сообщения' },
  { value: 'author', label: 'Автор' },
  { value: 'source', label: 'Источник' },
  { value: 'publication_title', label: 'Название публикации' },
  { value: 'url', label: 'URL' },
  { value: 'doi', label: 'DOI' },
  { value: 'tag', label: 'Метка' },
]

const OPERATOR_OPTIONS: { value: ConditionOperator; label: string }[] = [
  { value: 'contains', label: 'содержит' },
  { value: 'equals', label: 'равно' },
  { value: 'starts_with', label: 'начинается с' },
]

interface ConditionEditorProps {
  condition: ComplexQueryCondition
  onChange: (condition: ComplexQueryCondition) => void
  onDelete: () => void
}

function ConditionEditor({ condition, onChange, onDelete }: ConditionEditorProps) {
  return (
    <div className="condition-row">
      <div className="condition-negation">
        {condition.negated && <span className="not-badge">НЕ</span>}
      </div>

      <select
        value={condition.field}
        onChange={(e) => onChange({ ...condition, field: e.target.value as ConditionField })}
      >
        {FIELD_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      <select
        value={condition.operator}
        onChange={(e) => onChange({ ...condition, operator: e.target.value as ConditionOperator })}
      >
        {OPERATOR_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      <input
        type="text"
        value={condition.value}
        onChange={(e) => onChange({ ...condition, value: e.target.value })}
        placeholder="Значение"
        className="input"
      />

      <div className="condition-actions">
        <button
          type="button"
          className={`negate-btn ${condition.negated ? 'active' : ''}`}
          onClick={() => onChange({ ...condition, negated: !condition.negated })}
          title="Отрицание (НЕ)"
        >
          ¬
        </button>
        <button type="button" className="delete-btn" onClick={onDelete} title="Удалить">
          ×
        </button>
      </div>
    </div>
  )
}

interface GroupEditorProps {
  group: ComplexQueryGroup
  onChange: (group: ComplexQueryGroup) => void
  onDelete?: () => void
  depth?: number
  parentOperator?: 'AND' | 'OR'
}

function GroupEditor({ group, onChange, onDelete, depth = 0, parentOperator }: GroupEditorProps) {
  const [showAddMenu, setShowAddMenu] = useState<boolean>(false)

  const addCondition = (): void => {
    onChange({
      ...group,
      conditions: [...group.conditions, createEmptyCondition()],
    })
    setShowAddMenu(false)
  }

  const addGroup = (): void => {
    onChange({
      ...group,
      groups: [
        ...group.groups,
        { operator: 'AND', conditions: [], groups: [] },
      ],
    })
    setShowAddMenu(false)
  }

  const updateCondition = (index: number, condition: ComplexQueryCondition): void => {
    const newConditions = [...group.conditions]
    newConditions[index] = condition
    onChange({ ...group, conditions: newConditions })
  }

  const deleteCondition = (index: number): void => {
    const newConditions = group.conditions.filter((_: ComplexQueryCondition, i: number) => i !== index)
    onChange({ ...group, conditions: newConditions })
  }

  const updateGroup = (index: number, subGroup: ComplexQueryGroup): void => {
    const newGroups = [...group.groups]
    newGroups[index] = subGroup
    onChange({ ...group, groups: newGroups })
  }

  const deleteGroup = (index: number): void => {
    const newGroups = group.groups.filter((_: ComplexQueryGroup, i: number) => i !== index)
    onChange({ ...group, groups: newGroups })
  }

  // Показываем, как эта группа сочетается с родительской
  const getRelationHint = (): string => {
    if (parentOperator === 'AND') {
      return '⚠️ Эта группа будет выполнена вместе (И) с остальными условиями выше'
    }
    if (parentOperator === 'OR') {
      return '⚠️ Эта группа будет выполнена как вариант (ИЛИ) наряду с другими'
    }
    return ''
  }

  return (
    <div className={`group-editor depth-${Math.min(depth, 3)}`}>
      <div className="group-header">
        <div className="group-operator">
          <span className="operator-label">Оператор внутри группы:</span>
          <select
            value={group.operator}
            onChange={(e) => onChange({ ...group, operator: e.target.value as 'AND' | 'OR' })}
            className="operator-select"
          >
            <option value="AND">И (все условия должны выполняться)</option>
            <option value="OR">ИЛИ (достаточно одного условия)</option>
          </select>
        </div>

        <div className="group-actions">
          <div className="add-menu">
            <button
              type="button"
              className="btn-secondary small"
              onClick={() => setShowAddMenu(!showAddMenu)}
            >
              + Добавить
            </button>
            {showAddMenu && (
              <div className="add-menu-dropdown">
                <button type="button" onClick={addCondition}>
                  + Добавить условие
                </button>
                <button type="button" onClick={addGroup}>
                  + Добавить вложенную группу
                </button>
              </div>
            )}
          </div>

          {onDelete && (
            <button type="button" className="delete-group-btn" onClick={onDelete}>
              Удалить группу
            </button>
          )}
        </div>
      </div>

      {getRelationHint() && (
        <div className="group-hint">{getRelationHint()}</div>
      )}

      <div className="group-conditions">
        {group.conditions.length === 0 && group.groups.length === 0 && (
          <div className="empty-group-hint">
            Пустая группа. Нажмите "+ Добавить", чтобы добавить условие или вложенную группу.
          </div>
        )}

        {group.conditions.map((cond: ComplexQueryCondition, idx: number) => (
          <ConditionEditor
            key={`cond-${idx}`}
            condition={cond}
            onChange={(c: ComplexQueryCondition) => updateCondition(idx, c)}
            onDelete={() => deleteCondition(idx)}
          />
        ))}
      </div>

      <div className="group-groups">
        {group.groups.map((subGroup: ComplexQueryGroup, idx: number) => (
          <GroupEditor
            key={`group-${idx}`}
            group={subGroup}
            onChange={(g: ComplexQueryGroup) => updateGroup(idx, g)}
            onDelete={() => deleteGroup(idx)}
            depth={depth + 1}
            parentOperator={group.operator}
          />
        ))}
      </div>
    </div>
  )
}

export function ComplexQueryBuilder({ query, onChange, onClose }: ComplexQueryBuilderProps) {
  // Примеры запросов для обучения пользователя
  const examples = [
    {
      name: 'Пример 1: И + ИЛИ',
      description: '(Заголовок содержит "отчет" ИЛИ Текст содержит "анализ") И Автор начинается с "Иван"',
      build: () => {
        onChange({
          operator: 'AND',
          conditions: [],
          groups: [
            {
              operator: 'OR',
              conditions: [
                { field: 'title', operator: 'contains', value: 'отчет', negated: false },
                { field: 'content', operator: 'contains', value: 'анализ', negated: false },
              ],
              groups: [],
            },
            {
              operator: 'AND',
              conditions: [
                { field: 'author', operator: 'starts_with', value: 'Иван', negated: false },
              ],
              groups: [],
            },
          ],
        })
      },
    },
    {
      name: 'Пример 2: НЕ',
      description: 'Заголовок содержит "доклад" И НЕ Метка равна "черновик"',
      build: () => {
        onChange({
          operator: 'AND',
          conditions: [
            { field: 'title', operator: 'contains', value: 'доклад', negated: false },
            { field: 'tag', operator: 'equals', value: 'черновик', negated: true },
          ],
          groups: [],
        })
      },
    },
    {
      name: 'Пример 3: Сложный вложенный',
      description: '(Автор содержит "Петров" ИЛИ Автор содержит "Сидоров") И (Текст содержит "важно" ИЛИ Метка равна "срочно")',
      build: () => {
        onChange({
          operator: 'AND',
          conditions: [],
          groups: [
            {
              operator: 'OR',
              conditions: [
                { field: 'author', operator: 'contains', value: 'Петров', negated: false },
                { field: 'author', operator: 'contains', value: 'Сидоров', negated: false },
              ],
              groups: [],
            },
            {
              operator: 'OR',
              conditions: [
                { field: 'content', operator: 'contains', value: 'важно', negated: false },
                { field: 'tag', operator: 'equals', value: 'срочно', negated: false },
              ],
              groups: [],
            },
          ],
        })
      },
    },
  ]

  return (
    <div className="complex-query-modal">
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal-content complex-query-builder">
        <div className="modal-header">
          <h3>Сложный запрос</h3>
          <button type="button" className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="query-description">
            <p>
              <strong>Как это работает:</strong>
            </p>
            <ul>
              <li>У каждой <strong>группы</strong> свой оператор — <code>И</code> или <code>ИЛИ</code></li>
              <li>Группы можно <strong>вкладывать</strong> друг в друга</li>
              <li>К любому условию можно применить <strong>НЕ</strong> (кнопка <code>¬</code>)</li>
              <li>Пример: <code>(условие1 И условие2) ИЛИ (условие3 И условие4)</code></li>
            </ul>
          </div>

          <div className="examples-section">
            <p><strong>Быстрые примеры:</strong></p>
            <div className="examples-buttons">
              {examples.map((ex, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="btn-secondary small"
                  onClick={ex.build}
                >
                  {ex.name}
                </button>
              ))}
            </div>
          </div>

          <div className="query-builder-section">
            <p><strong>Ваш запрос:</strong></p>
            <GroupEditor group={query} onChange={onChange} />
          </div>
        </div>

        <div className="modal-footer">
          <button type="button" className="btn-primary" onClick={onClose}>
            Применить и выполнить поиск
          </button>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Отмена
          </button>
        </div>
      </div>
    </div>
  )
}