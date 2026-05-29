import { useEffect, useState } from "react";
import { Eye, EyeOff } from "lucide-react";

type InstanceFormMode = "source" | "target";

interface InstanceFormProps {
  mode?: InstanceFormMode;
  submitError?: string;
  submitLabel?: string;
  subdomainDisabled?: boolean;
  tokenPlaceholder?: string;
  /** true이면 API 토큰 필수(신규 등록), false이면 비워 두면 변경하지 않음(편집) */
  apiTokenRequired?: boolean;
  initialValues?: {
    name?: string;
    subdomain?: string;
    email?: string;
    apiToken?: string;
  };
  onSubmit: (payload: {
    name: string;
    subdomain: string;
    email: string;
    api_token: string;
  }) => Promise<void>;
}

export default function InstanceForm({
  onSubmit,
  submitError,
  submitLabel = "저장",
  subdomainDisabled = false,
  tokenPlaceholder = "토큰 입력",
  apiTokenRequired = true,
  initialValues,
}: InstanceFormProps) {
  const [name, setName] = useState("");
  const [subdomain, setSubdomain] = useState("");
  const [email, setEmail] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [showApiToken, setShowApiToken] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setName(initialValues?.name ?? "");
    setSubdomain(initialValues?.subdomain ?? "");
    setEmail(initialValues?.email ?? "");
    setApiToken(initialValues?.apiToken ?? "");
    setShowApiToken(false);
  }, [initialValues]);

  /**
   * 사용자가 이름을 비웠을 때 서브도메인 기반 기본 이름을 계산한다.
   * @param {string} rawName 사용자가 입력한 이름
   * @param {string} rawSubdomain 사용자가 입력한 서브도메인
   * @returns {string} 최종 저장에 사용할 인스턴스 이름
   */
  function resolveInstanceName(rawName: string, rawSubdomain: string): string {
    const trimmedName = rawName.trim();
    if (trimmedName.length > 0) {
      return trimmedName;
    }

    const normalizedSubdomain = rawSubdomain.trim().replace(".zendesk.com", "");
    if (normalizedSubdomain.includes(".")) {
      return normalizedSubdomain.split(".")[0].trim();
    }

    return normalizedSubdomain;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit({
        name: resolveInstanceName(name, subdomain),
        subdomain,
        email,
        api_token: apiToken,
      });
      setName("");
      setSubdomain("");
      setEmail("");
      setApiToken("");
      setShowApiToken(false);
    } catch {
      // 저장 실패 시에는 모달을 유지하고 상위에서 전달한 에러 메시지를 노출한다.
      return;
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="card form-grid" onSubmit={handleSubmit}>
      {submitError ? <p className="notice">{submitError}</p> : null}
      <label>
        이름
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="선택 입력 (비우면 서브도메인 자동 사용)"
        />
      </label>
      <label>
        서브도메인
        <input
          value={subdomain}
          onChange={(event) => setSubdomain(event.target.value)}
          placeholder="예: gssuper 또는 gssuper.zendesk.com"
          disabled={subdomainDisabled}
          required
        />
      </label>
      <label>
        이메일
        <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="예: user@company.com" required />
      </label>
      <label>
        API 토큰
        <div className="password-input-wrap">
          <input
            type={showApiToken ? "text" : "password"}
            value={apiToken}
            onChange={(event) => setApiToken(event.target.value)}
            placeholder={tokenPlaceholder}
            required={apiTokenRequired}
          />
          <button
            type="button"
            className="password-toggle-button"
            onClick={() => setShowApiToken((previous) => !previous)}
            aria-label={showApiToken ? "API 토큰 숨기기" : "API 토큰 보기"}
          >
            {showApiToken ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
          </button>
        </div>
      </label>
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "처리 중..." : submitLabel}
      </button>
    </form>
  );
}
