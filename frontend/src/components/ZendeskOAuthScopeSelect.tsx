import { useEffect, useId, useMemo, useRef, useState } from "react";
import { ChevronDown, Search, X } from "lucide-react";
import {
  DEFAULT_OAUTH_SCOPES,
  groupZendeskOAuthScopeOptions,
  parseOAuthScopesString,
  serializeOAuthScopes,
  ZENDESK_OAUTH_SCOPE_OPTION_BY_VALUE,
  ZENDESK_OAUTH_SCOPE_OPTIONS,
  ZENDESK_OAUTH_SCOPES_DOC_URL,
} from "../constants/zendeskOAuthScopes";

interface ZendeskOAuthScopeSelectProps {
  /** 공백으로 구분된 scope 문자열 */
  value: string;
  /** scope 변경 시 호출 */
  onChange: (value: string) => void;
  disabled?: boolean;
}

/**
 * Zendesk OAuth scope 멀티셀렉트 드롭다운(태그 필드 + 체크박스 목록).
 */
export default function ZendeskOAuthScopeSelect({
  value,
  onChange,
  disabled = false,
}: ZendeskOAuthScopeSelectProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listboxId = useId();
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const selectedScopes = useMemo(() => parseOAuthScopesString(value), [value]);
  const selectedSet = useMemo(() => new Set(selectedScopes), [selectedScopes]);

  const filteredOptionGroups = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();
    const matched = ZENDESK_OAUTH_SCOPE_OPTIONS.filter((option) => {
      if (!normalizedQuery) {
        return true;
      }
      return (
        option.value.toLowerCase().includes(normalizedQuery) ||
        option.label.toLowerCase().includes(normalizedQuery) ||
        option.group.toLowerCase().includes(normalizedQuery)
      );
    });
    return groupZendeskOAuthScopeOptions(matched);
  }, [searchQuery]);

  /** 문서 목록에 없는 legacy scope(태그로만 표시) */
  const legacyScopes = useMemo(
    () => selectedScopes.filter((scope) => !ZENDESK_OAUTH_SCOPE_OPTION_BY_VALUE.has(scope)),
    [selectedScopes],
  );

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      if (rootRef.current?.contains(event.target as Node)) {
        return;
      }
      setIsOpen(false);
      setSearchQuery("");
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const timer = window.setTimeout(() => searchInputRef.current?.focus(), 0);
    return () => window.clearTimeout(timer);
  }, [isOpen]);

  /**
   * 드롭다운 열림 상태를 토글한다.
   */
  function toggleDropdown() {
    if (disabled) {
      return;
    }
    setIsOpen((previous) => {
      if (previous) {
        setSearchQuery("");
      }
      return !previous;
    });
  }

  /**
   * scope 선택 여부를 변경한다.
   * @param scopeValue scope 문자열
   * @param checked 체크 여부
   */
  function toggleScope(scopeValue: string, checked: boolean) {
    if (disabled) {
      return;
    }
    if (checked) {
      if (selectedSet.has(scopeValue)) {
        return;
      }
      onChange(serializeOAuthScopes([...selectedScopes, scopeValue]));
      return;
    }
    onChange(serializeOAuthScopes(selectedScopes.filter((scope) => scope !== scopeValue)));
  }

  /**
   * 태그에서 scope를 제거한다.
   * @param scopeValue 제거할 scope
   */
  function removeScope(scopeValue: string) {
    if (disabled) {
      return;
    }
    onChange(serializeOAuthScopes(selectedScopes.filter((scope) => scope !== scopeValue)));
  }

  /**
   * 태그 툴팁용 라벨을 반환한다.
   * @param scopeValue scope 문자열
   */
  function resolveScopeLabel(scopeValue: string): string {
    return ZENDESK_OAUTH_SCOPE_OPTION_BY_VALUE.get(scopeValue)?.label ?? scopeValue;
  }

  return (
    <div className="oauth-scope-picker" ref={rootRef}>
      <div className={`oauth-scope-field${isOpen ? " is-open" : ""}${disabled ? " is-disabled" : ""}`}>
        <div
          role="combobox"
          tabIndex={disabled ? -1 : 0}
          className="oauth-scope-field-trigger"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          aria-controls={listboxId}
          aria-disabled={disabled}
          onClick={() => {
            if (!disabled) {
              toggleDropdown();
            }
          }}
          onKeyDown={(event) => {
            if (disabled) {
              return;
            }
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              toggleDropdown();
            }
          }}
        >
          <span className="oauth-scope-field-tags">
            {selectedScopes.length === 0 ? (
              <span className="oauth-scope-placeholder">scope 선택</span>
            ) : (
              selectedScopes.map((scopeValue) => (
                <span
                  key={scopeValue}
                  className={`oauth-scope-tag${legacyScopes.includes(scopeValue) ? " is-legacy" : ""}`}
                  title={resolveScopeLabel(scopeValue)}
                >
                  <span className="oauth-scope-tag-text">{scopeValue}</span>
                  <button
                    type="button"
                    className="oauth-scope-tag-remove"
                    disabled={disabled}
                    aria-label={`${scopeValue} scope 제거`}
                    onClick={(event) => {
                      event.stopPropagation();
                      removeScope(scopeValue);
                    }}
                  >
                    <X size={10} strokeWidth={2.25} aria-hidden="true" />
                  </button>
                </span>
              ))
            )}
          </span>
          <ChevronDown
            size={16}
            className={`oauth-scope-chevron${isOpen ? " is-open" : ""}`}
            aria-hidden="true"
          />
        </div>

        {isOpen ? (
          <div className="oauth-scope-dropdown" role="presentation">
            <div className="oauth-scope-search">
              <Search size={14} aria-hidden="true" />
              <input
                ref={searchInputRef}
                type="search"
                value={searchQuery}
                placeholder="scope 검색"
                aria-label="scope 검색"
                onChange={(event) => setSearchQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Escape") {
                    setIsOpen(false);
                    setSearchQuery("");
                  }
                }}
              />
            </div>

            <ul id={listboxId} className="oauth-scope-options" role="listbox" aria-multiselectable="true">
              {filteredOptionGroups.length === 0 ? (
                <li className="oauth-scope-options-empty muted">검색 결과가 없습니다.</li>
              ) : (
                filteredOptionGroups.map((group) => (
                  <li key={group.group} className="oauth-scope-option-group" role="presentation">
                    <p className="oauth-scope-option-group-label">{group.group}</p>
                    <ul role="group" aria-label={group.group}>
                      {group.options.map((option) => {
                        const isChecked = selectedSet.has(option.value);
                        return (
                          <li key={option.value} role="presentation">
                            <label className={`oauth-scope-option${isChecked ? " is-checked" : ""}`}>
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={(event) => toggleScope(option.value, event.target.checked)}
                              />
                              <span className="oauth-scope-option-value">{option.value}</span>
                              <span className="oauth-scope-option-desc">{option.label}</span>
                            </label>
                          </li>
                        );
                      })}
                    </ul>
                  </li>
                ))
              )}
            </ul>
          </div>
        ) : null}
      </div>

      <span className="form-hint">
        Zendesk OAuth{" "}
        <a href={ZENDESK_OAUTH_SCOPES_DOC_URL} target="_blank" rel="noreferrer">
          공식 scope 문서
        </a>
        기준 멀티 선택입니다. Help Center 마이그레이션에는 보통 <code>read</code>, <code>write</code> 또는{" "}
        <code>hc:read</code>, <code>hc:write</code>를 사용합니다.
      </span>
    </div>
  );
}

export {
  DEFAULT_OAUTH_SCOPES,
  parseOAuthScopesString,
  serializeOAuthScopes,
};
