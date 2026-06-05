import { useEffect, useState } from "react";

import { Eye, EyeOff, Link2 } from "lucide-react";

import ZendeskOAuthScopeSelect, {

  DEFAULT_OAUTH_SCOPES,

  parseOAuthScopesString,

  serializeOAuthScopes,

} from "./ZendeskOAuthScopeSelect";



/** 인스턴스별 Zendesk OAuth 클라이언트 + 연결 폼 입력 */

export interface InstanceOAuthFormValues {

  name: string;

  subdomain: string;

  email: string;

  oauth_client_id: string;

  oauth_client_secret: string;

  oauth_scopes: string;

}



interface InstanceFormProps {

  submitError?: string;

  oauthLabel?: string;

  subdomainDisabled?: boolean;

  /** true이면 Secret 비우고 연결 시 DB에 저장된 Secret 유지(재연결) */

  secretOptional?: boolean;

  /** true이면 연결 계정(이메일) 입력·저장 가능(수정 모달) */

  emailEditable?: boolean;

  initialValues?: Partial<InstanceOAuthFormValues>;

  onOAuthConnect: (payload: InstanceOAuthFormValues) => Promise<void>;

}



const DEFAULT_SCOPES = serializeOAuthScopes(DEFAULT_OAUTH_SCOPES);



export default function InstanceForm({

  onOAuthConnect,

  submitError,

  oauthLabel = "Zendesk OAuth 연결",

  subdomainDisabled = false,

  secretOptional = false,

  emailEditable = false,

  initialValues,

}: InstanceFormProps) {

  const [name, setName] = useState("");

  const [subdomain, setSubdomain] = useState("");

  const [email, setEmail] = useState("");

  const [oauthClientId, setOauthClientId] = useState("");

  const [oauthClientSecret, setOauthClientSecret] = useState("");

  const [oauthScopes, setOauthScopes] = useState(DEFAULT_SCOPES);

  const [showSecret, setShowSecret] = useState(false);

  const [isConnecting, setIsConnecting] = useState(false);



  useEffect(() => {

    setName(initialValues?.name ?? "");

    setSubdomain(initialValues?.subdomain ?? "");

    setEmail(initialValues?.email ?? "");

    setOauthClientId(initialValues?.oauth_client_id ?? "");

    setOauthClientSecret(initialValues?.oauth_client_secret ?? "");

    const scopeRaw = initialValues?.oauth_scopes?.trim();

    setOauthScopes(scopeRaw && parseOAuthScopesString(scopeRaw).length > 0 ? scopeRaw : DEFAULT_SCOPES);

    setShowSecret(false);

  }, [initialValues]);



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



  /**

   * 폼 입력값을 API 전송용 객체로 만든다.

   */

  function buildFormPayload(): InstanceOAuthFormValues {

    return {

      name: resolveInstanceName(name, subdomain),

      subdomain,

      email: email.trim(),

      oauth_client_id: oauthClientId.trim(),

      oauth_client_secret: oauthClientSecret.trim(),

      oauth_scopes: oauthScopes.trim() || DEFAULT_SCOPES,

    };

  }



  async function handleOAuthConnect() {

    const normalizedSubdomain = subdomain.trim().replace(".zendesk.com", "");

    if (!normalizedSubdomain) {

      return;

    }

    if (!oauthClientId.trim()) {

      return;

    }

    if (!secretOptional && !oauthClientSecret.trim()) {

      return;

    }

    if (emailEditable && !email.trim()) {

      return;

    }



    setIsConnecting(true);

    try {

      await onOAuthConnect(buildFormPayload());

    } catch {

      return;

    } finally {

      setIsConnecting(false);

    }

  }



  const canSubmit =

    subdomain.trim().length > 0 &&

    oauthClientId.trim().length > 0 &&

    (secretOptional || oauthClientSecret.trim().length > 0) &&

    (!emailEditable || email.trim().length > 0);



  return (

    <div className="card form-grid">

      {submitError ? <p className="notice">{submitError}</p> : null}

      <p className="form-intro">

        Zendesk Admin Center의 <strong>confidential OAuth 클라이언트</strong>(Identifier·Secret)로 백엔드에서

        토큰을 발급합니다. API 호출 권한은 <strong>해당 클라이언트를 만든 Zendesk 사용자</strong>와 동일합니다.

      </p>

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

          placeholder="예: company-a (company-a.zendesk.com)"

          disabled={subdomainDisabled}

          required

        />

      </label>

      {emailEditable ? (

        <label>

          연결 계정 (이메일)

          <input

            type="email"

            value={email}

            onChange={(event) => setEmail(event.target.value)}

            placeholder="표시·구분용 (연결 시 OAuth 클라이언트 소유자 이메일로 갱신됨)"

            required

          />

        </label>

      ) : null}

      <label>

        OAuth Client Identifier

        <input

          value={oauthClientId}

          onChange={(event) => setOauthClientId(event.target.value)}

          placeholder="Admin Center OAuth 클라이언트의 Unique identifier (표시 이름 아님)"

          required

        />

        <span className="form-hint">

          Admin Center의 <strong>Unique identifier</strong>와 동일해야 합니다.

        </span>

      </label>

      <label>

        OAuth Client Secret

        <div className="password-input-wrap">

          <input

            type={showSecret ? "text" : "password"}

            value={oauthClientSecret}

            onChange={(event) => setOauthClientSecret(event.target.value)}

            placeholder={secretOptional ? "변경할 때만 입력 (비우면 기존 Secret 유지)" : "해당 Zendesk용 Secret"}

            required={!secretOptional}

          />

          <button

            type="button"

            className="password-toggle-button"

            onClick={() => setShowSecret((previous) => !previous)}

            aria-label={showSecret ? "Secret 숨기기" : "Secret 보기"}

          >

            {showSecret ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}

          </button>

        </div>

      </label>

      <label>

        OAuth Scopes

        <ZendeskOAuthScopeSelect

          value={oauthScopes}

          onChange={setOauthScopes}

          disabled={isConnecting}

        />

      </label>

      <button

        type="button"

        className="oauth-connect-button"

        disabled={isConnecting || !canSubmit}

        onClick={() => void handleOAuthConnect()}

      >

        <Link2 size={16} aria-hidden="true" />

        {isConnecting ? "연결 중..." : oauthLabel}

      </button>

    </div>

  );

}


