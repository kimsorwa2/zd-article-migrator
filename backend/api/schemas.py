from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OAuthConnectRequest(BaseModel):
    """
    /**
     * Zendesk Client Credentials OAuth 연결 요청.
     * confidential OAuth 클라이언트 Identifier·Secret으로 백엔드에서 토큰을 발급한다.
     */
    """

    subdomain: str = Field(min_length=1, max_length=255)
    oauth_client_id: str = Field(min_length=1, max_length=255)
    oauth_client_secret: str = Field(min_length=1, max_length=2048)
    oauth_scopes: str | None = Field(default=None, max_length=255)
    name: str | None = Field(default=None, max_length=255)
    instance_id: int | None = Field(default=None, ge=1)
    selected_brand_ids: list[int] = Field(default_factory=list)


class SourceBrandPreviewRequest(BaseModel):
    """
    /**
     * 저장된 OAuth 토큰으로 브랜드 목록을 미리 본다.
     * @param {int} instance_id 인스턴스 ID
     */
    """

    instance_id: int = Field(ge=1)


class SourceBrandResponse(BaseModel):
    """
    /**
     * 소스 인스턴스의 브랜드 정보를 응답으로 전달한다.
     * @param {int} id 로컬 브랜드 ID(미리보기 API는 0)
     * @param {int} a_brand_id 소스 Zendesk 브랜드 ID
     * @param {str} name 브랜드 이름
     * @param {str} subdomain 브랜드 서브도메인
     * @param {bool} has_help_center Help Center 보유 여부
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    id: int = 0
    a_brand_id: int
    name: str
    subdomain: str
    has_help_center: bool = True


class CreateInstanceRequest(BaseModel):
    """
    /**
     * @deprecated OAuth connect로 인스턴스가 생성됩니다. 하위 호환용 스키마.
     */
    """

    name: str | None = Field(default=None, max_length=255)
    subdomain: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=255)
    api_token: str = Field(min_length=1, max_length=255)
    selected_brand_ids: list[int] = Field(default_factory=list)


class CreateSourceInstanceRequest(CreateInstanceRequest):
    """
    /**
     * 하위 호환용 소스 인스턴스 생성 요청 스키마를 정의한다.
     * @returns {None} 요청 스키마이므로 반환값 없음
     */
    """

    pass


class CreateTargetInstanceRequest(BaseModel):
    """@deprecated OAuth connect 사용."""

    name: str | None = Field(default=None, max_length=255)
    subdomain: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=255)
    api_token: str = Field(min_length=1, max_length=255)


class InstanceResponse(BaseModel):
    """
    /**
     * 인스턴스 기본 응답 스키마를 정의한다.
     * @param {int} id 인스턴스 PK
     * @param {str} name 인스턴스 별칭
     * @param {str} subdomain Zendesk 서브도메인
     * @param {str} email 인증 이메일
     * @param {str} role source 또는 target
     * @param {bool} is_active 사용 가능 여부
     * @param {datetime | None} last_fetched_at 마지막 데이터 수집 일시
     * @param {datetime} created_at 생성 일시
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    subdomain: str
    email: str
    oauth_connected: bool = False
    oauth_client_id: str = ""
    oauth_redirect_uri: str = ""
    oauth_scopes: str = ""
    oauth_client_configured: bool = False
    role: str
    is_active: bool
    last_fetched_at: datetime | None
    created_at: datetime


class InstanceDetailResponse(InstanceResponse):
    """
    /**
     * 인스턴스 상세 응답 스키마를 정의한다.
     * @param {list[SourceBrandResponse]} brands 인스턴스에 연결된 브랜드 목록
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    brands: list[SourceBrandResponse] = Field(default_factory=list)


class SourceInstanceResponse(InstanceDetailResponse):
    """
    /**
     * 하위 호환용 소스 인스턴스 상세 응답 스키마를 정의한다.
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    pass


class UpdateInstanceActiveRequest(BaseModel):
    """
    /**
     * 인스턴스 활성 상태 변경 요청 스키마를 정의한다.
     * @param {bool} is_active 활성화 여부
     * @returns {None} 요청 스키마이므로 반환값 없음
     */
    """

    is_active: bool


class UpdateInstanceRequest(BaseModel):
    """
    /**
     * 인스턴스 메타·OAuth 클라이언트 설정 수정(토큰은 Zendesk 연결로 갱신).
     */
    """

    name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    oauth_client_id: str | None = Field(default=None, max_length=255)
    oauth_client_secret: str | None = Field(default=None, max_length=2048)
    oauth_scopes: str | None = Field(default=None, max_length=255)


class ConnectionTestResponse(BaseModel):
    """
    /**
     * Zendesk 연결 테스트 결과 응답 스키마를 정의한다.
     * @param {bool} success 연결 성공 여부
     * @param {str} message 결과 메시지
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    success: bool
    message: str


class SyncCountsResponse(BaseModel):
    """
    /**
     * 동기화 처리 건수 응답 스키마를 정의한다.
     * @param {int} created 신규 생성 건수
     * @param {int} updated 기존 수정 건수
     * @param {int} deleted 삭제 건수
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    created: int
    updated: int
    deleted: int


class FetchBrandSummaryResponse(BaseModel):
    """
    /**
     * 브랜드 단위 수집 결과 요약 정보를 정의한다.
     * @param {int} brand_id 내부 브랜드 PK
     * @param {str} brand_name 브랜드 이름
     * @param {SyncCountsResponse} categories 카테고리 동기화 결과
     * @param {SyncCountsResponse} sections 섹션 동기화 결과
     * @param {SyncCountsResponse} articles 아티클 동기화 결과
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    brand_id: int
    brand_name: str
    categories: SyncCountsResponse
    sections: SyncCountsResponse
    articles: SyncCountsResponse


class FetchSyncResponse(BaseModel):
    """
    /**
     * 데이터 수집 실행 결과를 정의한다.
     * @param {int} instance_id 수집 대상 인스턴스 ID
     * @param {int} processed_brands 처리된 브랜드 수
     * @param {list[FetchBrandSummaryResponse]} brand_summaries 브랜드별 상세 결과
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    instance_id: int
    processed_brands: int
    brand_summaries: list[FetchBrandSummaryResponse] = Field(default_factory=list)


class FetchSyncStartResponse(BaseModel):
    """
    /**
     * 백그라운드 수집 작업 시작 응답을 정의한다.
     * @param {int} instance_id 수집 대상 인스턴스 ID
     * @param {str} status 작업 상태(running)
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    instance_id: int
    status: str = "running"


class FetchSyncWarningItem(BaseModel):
    """수집 중단 없이 기록된 경고 한 건."""

    timestamp: str
    phase: str = ""
    brand_name: str = ""
    message: str


class FetchSyncProgressResponse(BaseModel):
    """
    /**
     * 수집 진행률 폴링 응답을 정의한다.
     * @param {int} instance_id 인스턴스 ID
     * @param {str} status idle|running|completed|failed
     * @param {int} percent 진행률(0-100)
     * @param {str} message 사용자 표시 메시지
     * @param {str} phase 현재 단계 식별자
     * @param {int} brand_index 현재 브랜드 순번(1부터)
     * @param {int} brand_total 전체 브랜드 수
     * @param {str | None} brand_name 현재 브랜드 이름
     * @param {int} article_page 아티클 API 페이지 번호
     * @param {int} articles_collected 수집된 아티클 수
     * @param {int} attachments_checked 첨부 확인 완료 수
     * @param {int} attachments_total 첨부 확인 대상 수
     * @param {str | None} error 실패 시 오류 메시지
     * @param {FetchSyncResponse | None} result 완료 시 수집 결과
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    instance_id: int
    status: str
    percent: int = 0
    message: str = ""
    phase: str = ""
    brand_index: int = 0
    brand_total: int = 0
    brand_name: str | None = None
    article_page: int = 0
    articles_collected: int = 0
    attachments_checked: int = 0
    attachments_total: int = 0
    error: str | None = None
    result: FetchSyncResponse | None = None
    warnings: list[FetchSyncWarningItem] = Field(default_factory=list)


class FetchDetailArticleResponse(BaseModel):
    """
    /**
     * 수집 상세 트리의 아티클 노드를 정의한다.
     * @param {int} id 로컬 아티클 ID
     * @param {int} a_id 소스 아티클 A ID
     * @param {str} title 아티클 제목
     * @param {bool} draft 초안 여부
     * @param {str} html_url Help Center 아티클 URL
     * @param {bool} has_attachments 첨부파일 존재 여부
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    id: int
    a_id: int
    title: str
    draft: bool
    html_url: str
    has_attachments: bool


class FetchDetailSectionResponse(BaseModel):
    """
    /**
     * 수집 상세 트리의 섹션 노드를 정의한다.
     * @param {int} id 로컬 섹션 ID
     * @param {int} a_id 소스 섹션 A ID
     * @param {str} name 섹션 이름
     * @param {list[FetchDetailArticleResponse]} articles 이 섹션에 직접 속한 아티클
     * @param {list[FetchDetailSectionResponse]} children 하위 섹션(parent_section_id)
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    a_id: int
    name: str
    articles: list[FetchDetailArticleResponse] = Field(default_factory=list)
    children: list["FetchDetailSectionResponse"] = Field(default_factory=list)


class FetchDetailCategoryResponse(BaseModel):
    """
    /**
     * 수집 상세 트리의 카테고리 노드를 정의한다.
     * @param {int} id 로컬 카테고리 ID
     * @param {int} a_id 소스 카테고리 A ID
     * @param {str} name 카테고리 이름
     * @param {list[FetchDetailSectionResponse]} sections 하위 섹션 목록
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    id: int
    a_id: int
    name: str
    sections: list[FetchDetailSectionResponse] = Field(default_factory=list)


class FetchDetailBrandResponse(BaseModel):
    """
    /**
     * 수집 상세 트리의 브랜드 노드를 정의한다.
     * @param {int} id 로컬 브랜드 ID
     * @param {int} a_brand_id 소스 브랜드 A ID
     * @param {str} name 브랜드 이름
     * @param {str} subdomain 브랜드 서브도메인
     * @param {bool} has_help_center Help Center 보유 여부
     * @param {list[FetchDetailCategoryResponse]} categories 하위 카테고리 목록
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    id: int
    a_brand_id: int
    name: str
    subdomain: str
    has_help_center: bool
    categories: list[FetchDetailCategoryResponse] = Field(default_factory=list)


class FetchDetailSummaryResponse(BaseModel):
    """
    /**
     * 수집된 데이터 전체 요약 정보를 정의한다.
     * @param {int} total_brands 브랜드 수
     * @param {int} total_categories 카테고리 수
     * @param {int} total_sections 섹션 수
     * @param {int} total_articles 아티클 수
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    total_brands: int
    total_categories: int
    total_sections: int
    total_articles: int


class FetchDetailResponse(BaseModel):
    """
    /**
     * 수집된 소스 인스턴스 상세 데이터 응답 스키마를 정의한다.
     * @param {int} instance_id 인스턴스 ID
     * @param {str} instance_name 인스턴스 표시 이름
     * @param {datetime | None} last_fetched_at 마지막 수집 일시
     * @param {FetchDetailSummaryResponse} summary 전체 요약
     * @param {list[FetchDetailBrandResponse]} brands 브랜드 트리
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    instance_id: int
    instance_name: str
    last_fetched_at: datetime | None
    summary: FetchDetailSummaryResponse
    brands: list[FetchDetailBrandResponse] = Field(default_factory=list)


class MigrateExecuteRequest(BaseModel):
    """
    /**
     * 마이그레이션 실행 요청 스키마를 정의한다.
     * @param {int} source_instance_id 소스 인스턴스 ID
     * @param {int} target_instance_id 타겟 인스턴스 ID
     * @param {"skip" | "update" | "force"} duplicate_policy 중복 처리 정책
     * @param {list[int]} brand_ids 선택한 브랜드 로컬 ID 목록
     * @param {list[int]} category_ids 선택한 카테고리 로컬 ID 목록
     * @param {list[int]} section_ids 선택한 섹션 로컬 ID 목록
     * @param {list[int]} article_ids 선택한 아티클 로컬 ID 목록
     * @returns {None} 요청 스키마이므로 반환값 없음
     */
    """

    source_instance_id: int
    target_instance_id: int
    duplicate_policy: Literal["skip", "update", "force"] = "skip"
    brand_ids: list[int] = Field(default_factory=list)
    category_ids: list[int] = Field(default_factory=list)
    section_ids: list[int] = Field(default_factory=list)
    article_ids: list[int] = Field(default_factory=list)
    target_brand_id: int | None = Field(
        default=None,
        description="타겟 Help Center 브랜드 로컬 ID. 타겟에 브랜드가 여러 개일 때 필수.",
    )


class MigrateSummaryResponse(BaseModel):
    """
    /**
     * 마이그레이션 처리 요약 정보를 정의한다.
     * @param {int} brands 처리된 브랜드 건수
     * @param {int} categories 처리된 카테고리 건수
     * @param {int} sections 처리된 섹션 건수
     * @param {int} articles 처리된 아티클 건수
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    brands: int
    categories: int
    sections: int
    articles: int
    scope_categories: int = 0
    scope_sections: int = 0
    scope_articles: int = 0


class MigrateExecuteResponse(BaseModel):
    """
    /**
     * 마이그레이션 실행 응답 스키마를 정의한다.
     */
    """

    source_instance_id: int
    target_instance_id: int
    summary: MigrateSummaryResponse


class MigrateExecuteStartResponse(BaseModel):
    """
    /**
     * 마이그레이션 백그라운드 작업 시작 응답.
     */
    """

    source_instance_id: int
    target_instance_id: int
    status: str


class MigrateProgressResponse(BaseModel):
    """
    /**
     * 마이그레이션 진행률 폴링 응답.
     */
    """

    source_instance_id: int
    target_instance_id: int
    status: Literal["idle", "running", "completed", "failed"]
    percent: int
    message: str
    phase: str
    current_step: int
    total_steps: int
    error: str | None = None
    result: MigrateExecuteResponse | None = None
    logs: list[str] = Field(default_factory=list)


class MigrateOverlayItemResponse(BaseModel):
    """
    /**
     * 타겟 트리 오버레이용 매핑 항목.
     */
    """

    mapping_id: int
    mapping_entity_type: str
    source_a_id: int
    target_a_id: int
    status: str
    error_message: str | None = None


class MigrateOverlayResponse(BaseModel):
    """
    /**
     * 타겟 Help Center 트리 하이라이트용 오버레이 응답.
     */
    """

    source_instance_id: int
    target_instance_id: int
    items: list[MigrateOverlayItemResponse] = Field(default_factory=list)
    migrated_target_category_a_ids: list[int] = Field(default_factory=list)
    migrated_target_section_a_ids: list[int] = Field(default_factory=list)
    migrated_target_article_a_ids: list[int] = Field(default_factory=list)
    delete_error_target_category_a_ids: list[int] = Field(default_factory=list)
    delete_error_target_section_a_ids: list[int] = Field(default_factory=list)
    delete_error_target_article_a_ids: list[int] = Field(default_factory=list)
    delete_error_items: list[MigrateOverlayItemResponse] = Field(default_factory=list)


class MigrateTreeArticleResponse(BaseModel):
    """
    /**
     * 마이그레이션 트리의 아티클 노드 응답을 정의한다.
     * @param {int} id 로컬 아티클 ID
     * @param {int} a_id 소스 아티클 A ID
     * @param {str} title 아티클 제목
     * @param {str} status 매핑 상태값 또는 unmapped
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    id: int
    a_id: int
    title: str
    status: str


class MigrateTreeSectionResponse(BaseModel):
    """
    /**
     * 마이그레이션 트리의 섹션 노드 응답을 정의한다.
     * @param {int} id 로컬 섹션 ID
     * @param {int} a_id 소스 섹션 A ID
     * @param {str} name 섹션 이름
     * @param {str} status 매핑 상태값 또는 unmapped
     * @param {list[MigrateTreeArticleResponse]} articles 하위 아티클 목록
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    id: int
    a_id: int
    name: str
    status: str
    articles: list[MigrateTreeArticleResponse] = Field(default_factory=list)


class MigrateTreeCategoryResponse(BaseModel):
    """
    /**
     * 마이그레이션 트리의 카테고리 노드 응답을 정의한다.
     * @param {int} id 로컬 카테고리 ID
     * @param {int} a_id 소스 카테고리 A ID
     * @param {str} name 카테고리 이름
     * @param {str} status 매핑 상태값 또는 unmapped
     * @param {list[MigrateTreeSectionResponse]} sections 하위 섹션 목록
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    id: int
    a_id: int
    name: str
    status: str
    sections: list[MigrateTreeSectionResponse] = Field(default_factory=list)


class MigrateTreeBrandResponse(BaseModel):
    """
    /**
     * 마이그레이션 트리의 브랜드 노드 응답을 정의한다.
     * @param {int} id 로컬 브랜드 ID
     * @param {int} a_brand_id 소스 브랜드 A ID
     * @param {str} name 브랜드 이름
     * @param {str} status 매핑 상태값 또는 unmapped
     * @param {list[MigrateTreeCategoryResponse]} categories 하위 카테고리 목록
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    id: int
    a_brand_id: int
    name: str
    status: str
    categories: list[MigrateTreeCategoryResponse] = Field(default_factory=list)


class MigrateTargetTreeResponse(BaseModel):
    """
    /**
     * 마이그레이션으로 생성·저장된 타겟 Help Center 트리 응답.
     * FetchDetailResponse와 동일한 brands 구조를 사용해 프론트 트리 컴포넌트를 재사용한다.
     */
    """

    source_instance_id: int
    target_instance_id: int
    instance_id: int
    instance_name: str
    summary: FetchDetailSummaryResponse
    brands: list[FetchDetailBrandResponse] = Field(default_factory=list)
    mapping_record_count: int = 0


class MigrateClearMappingsResponse(BaseModel):
    """
    /**
     * 소스·타겟 쌍의 migration_mappings 삭제 결과.
     */
    """

    source_instance_id: int
    target_instance_id: int
    deleted_count: int


class MigrateTreeResponse(BaseModel):
    """
    /**
     * 마이그레이션 선택 트리 응답 스키마를 정의한다.
     * @param {int} source_instance_id 소스 인스턴스 ID
     * @param {int} target_instance_id 타겟 인스턴스 ID
     * @param {list[MigrateTreeBrandResponse]} brands 브랜드 루트 노드 목록
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    source_instance_id: int
    target_instance_id: int
    brands: list[MigrateTreeBrandResponse] = Field(default_factory=list)


class DeleteExecuteRequest(BaseModel):
    """
    /**
     * 삭제 실행/미리보기 요청 스키마를 정의한다.
     * @param {int} source_instance_id 소스 인스턴스 ID
     * @param {int} target_instance_id 타겟 인스턴스 ID
     * @param {list[int]} brand_a_ids 선택한 소스 브랜드 A ID 목록
     * @param {list[int]} category_a_ids 선택한 소스 카테고리 A ID 목록
     * @param {list[int]} section_a_ids 선택한 소스 섹션 A ID 목록
     * @param {list[int]} article_a_ids 선택한 소스 아티클 A ID 목록
     * @returns {None} 요청 스키마이므로 반환값 없음
     */
    """

    source_instance_id: int
    target_instance_id: int
    brand_a_ids: list[int] = Field(default_factory=list)
    category_a_ids: list[int] = Field(default_factory=list)
    section_a_ids: list[int] = Field(default_factory=list)
    article_a_ids: list[int] = Field(default_factory=list)
    target_category_a_ids: list[int] = Field(default_factory=list)
    target_section_a_ids: list[int] = Field(default_factory=list)
    target_article_a_ids: list[int] = Field(default_factory=list)
    target_brand_id: int | None = Field(
        default=None,
        description="타겟 Help Center 브랜드 로컬 ID. 타겟에 브랜드가 여러 개일 때 필수.",
    )


class DeleteSummaryResponse(BaseModel):
    """
    /**
     * 삭제 처리 요약 정보를 정의한다.
     * @param {int} categories 삭제된 카테고리 수
     * @param {int} sections 삭제된 섹션 수
     * @param {int} articles 삭제된 아티클 수
     * @returns {None} 응답 스키마이므로 반환값 없음
     */
    """

    categories: int
    sections: int
    articles: int


class DeleteFailedItemResponse(BaseModel):
    """
    /**
     * 삭제 실패한 매핑 항목 응답.
     */
    """

    mapping_id: int
    entity_type: str
    target_a_id: int
    error_message: str


class DeleteExecuteResponse(BaseModel):
    """
    /**
     * 삭제 실행/재시도 응답 스키마를 정의한다.
     */
    """

    source_instance_id: int
    target_instance_id: int
    summary: DeleteSummaryResponse
    failed_items: list[DeleteFailedItemResponse] = Field(default_factory=list)


class DeleteRetryRequest(BaseModel):
    """
    /**
     * 삭제 실패 항목 재시도 요청.
     */
    """

    source_instance_id: int
    target_instance_id: int
    target_brand_id: int | None = None
    mapping_ids: list[int] = Field(
        default_factory=list,
        description="비어 있으면 해당 인스턴스 쌍의 delete_error 전체를 재시도한다.",
    )


class AiOcrModelOptionResponse(BaseModel):
    """Vision 모델 셀렉트 옵션."""

    value: str
    label: str


class AiOcrModelOptionsResponse(BaseModel):
    """제공자별 선택 가능한 Vision 모델 목록."""

    gemini: list[AiOcrModelOptionResponse] = Field(default_factory=list)
    openai: list[AiOcrModelOptionResponse] = Field(default_factory=list)
    bedrock: list[AiOcrModelOptionResponse] = Field(default_factory=list)
    # Bedrock: 리전별 inference profile ID 예시 (foundation → apac.* 등)
    bedrock_inference_profiles: list[AiOcrModelOptionResponse] = Field(default_factory=list)
    defaults: dict[str, str] = Field(default_factory=dict)


class AiOcrProviderConfigResponse(BaseModel):
    """AI 제공자별 계정·키·모델 요약."""

    account: str | None = None
    has_api_key: bool = False
    api_key_masked: str | None = None
    model: str


class AiOcrPromptTemplateResponse(BaseModel):
    """저장된 OCR Vision 프롬프트 템플릿."""

    id: int
    name: str
    description: str | None = None
    system_prompt: str
    user_prompt: str
    is_builtin: bool = False
    created_at: datetime
    updated_at: datetime


class AiOcrConnectionResponse(BaseModel):
    """AI Vision 연동 프로필 한 건."""

    id: int
    provider: Literal["gemini", "openai", "bedrock"]
    model: str
    account: str | None = None
    has_api_key: bool = False
    api_key_masked: str | None = None
    has_api_secret: bool = False
    api_secret_masked: str | None = None
    aws_region: str | None = None
    label: str
    is_active: bool = False
    prompt_template_id: int | None = None
    prompt_template_name: str | None = None
    created_at: datetime
    updated_at: datetime


# Bedrock 단기 API 키는 1000자 이상일 수 있음 (장기 키는 약 132자)
AI_OCR_CONNECTION_API_KEY_MAX_LENGTH = 4096


class AiOcrConnectionCreateRequest(BaseModel):
    """AI 연동 프로필 추가 요청."""

    provider: Literal["gemini", "openai", "bedrock"]
    model: str = Field(min_length=1, max_length=128)
    account: str | None = Field(default=None, max_length=255)
    api_key: str | None = Field(default=None, max_length=AI_OCR_CONNECTION_API_KEY_MAX_LENGTH)
    api_secret: str | None = Field(default=None, max_length=512, description="(미사용) 레거시 필드")
    aws_region: str | None = Field(default=None, max_length=32)
    prompt_template_id: int | None = Field(default=None, description="이 연동에 쓸 OCR 프롬프트 템플릿 ID")
    set_active: bool = Field(default=True)


class AiOcrConnectionTestResponse(BaseModel):
    """AI 연동 프로필 연결 테스트 결과."""

    success: bool
    message: str
    provider: Literal["gemini", "openai", "bedrock"]
    model: str
    latency_ms: int | None = None


class AiOcrConnectionUpdateRequest(BaseModel):
    """AI 연동 프로필 수정 요청."""

    model: str | None = Field(default=None, max_length=128)
    account: str | None = Field(default=None, max_length=255)
    api_key: str | None = Field(
        default=None,
        max_length=AI_OCR_CONNECTION_API_KEY_MAX_LENGTH,
        description="비우면 기존 키 유지",
    )
    api_secret: str | None = Field(default=None, max_length=512, description="비우면 기존 Secret 유지")
    aws_region: str | None = Field(default=None, max_length=32)
    prompt_template_id: int | None = Field(default=None, description="이 연동에 쓸 OCR 프롬프트 템플릿 ID")


class AiOcrSettingsResponse(BaseModel):
    """AI-OCR 설정 응답."""

    active_provider: Literal["gemini", "openai", "bedrock"]
    active_connection_id: int | None = None
    active_prompt_id: int | None = None
    connections: list[AiOcrConnectionResponse] = Field(default_factory=list)
    gemini: AiOcrProviderConfigResponse
    openai: AiOcrProviderConfigResponse
    prompt_templates: list[AiOcrPromptTemplateResponse] = Field(default_factory=list)
    default_system_prompt: str
    default_user_prompt: str


class AiOcrSettingsUpdateRequest(BaseModel):
    """AI-OCR 설정 저장 요청."""

    active_provider: Literal["gemini", "openai", "bedrock"] | None = None
    active_connection_id: int | None = Field(default=None, description="OCR에 사용할 연동 프로필 ID")
    active_prompt_id: int | None = Field(default=None, description="OCR 분석에 사용할 프롬프트 템플릿 ID")
    gemini_account: str | None = Field(default=None, max_length=255)
    gemini_api_key: str | None = Field(
        default=None,
        max_length=512,
        description="비우면 기존 Gemini 키 유지",
    )
    openai_account: str | None = Field(default=None, max_length=255)
    openai_api_key: str | None = Field(
        default=None,
        max_length=512,
        description="비우면 기존 OpenAI 키 유지",
    )
    gemini_model: str | None = Field(default=None, max_length=64, description="Gemini Vision 모델 ID")
    openai_model: str | None = Field(default=None, max_length=64, description="OpenAI Vision 모델 ID")


class AiOcrPromptTemplateCreateRequest(BaseModel):
    """프롬프트 템플릿 생성 요청."""

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    set_active: bool = Field(default=False, description="생성 후 OCR 활성 프롬프트로 지정")


class AiOcrPromptTemplateUpdateRequest(BaseModel):
    """프롬프트 템플릿 수정 요청."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    system_prompt: str | None = Field(default=None, min_length=1)
    user_prompt: str | None = Field(default=None, min_length=1)


class AiOcrLogEntryResponse(BaseModel):
    """AI-OCR 작업 로그 한 건."""

    timestamp: str
    level: Literal["info", "error", "success"]
    summary: str
    body: str


class AiOcrAnalyzeResponse(BaseModel):
    """이미지 OCR 분석 결과."""

    history_id: int
    title: str
    html_body: str
    label_names: list[str]
    detected_product: str
    maintenance_cycle: str | None = None
    body_preview_text: str
    logs: list[AiOcrLogEntryResponse] = Field(default_factory=list)


class AiOcrAnalysisHistoryItem(BaseModel):
    """저장된 OCR 분석 이력 한 건."""

    id: int
    label: str
    display_label: str | None = None
    ai_model: str | None = None
    source_filename: str
    title: str
    html_body: str
    label_names: list[str]
    detected_product: str
    maintenance_cycle: str | None = None
    body_preview_text: str
    prompt_template_id: int | None = None
    image_size_kb: int | None = None
    preprocessed: bool | None = None
    processed_image_size_kb: int | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    thinking_tokens: int | None = None
    total_tokens: int | None = None
    finish_reason: str | None = None
    parse_success: bool | None = None
    experiment_tag: str | None = None
    raw_response_text: str | None = None
    parse_error_message: str | None = None
    used_system_prompt: str | None = None
    used_user_prompt: str | None = None
    created_at: datetime


class AiOcrAnalysisHistoryListResponse(BaseModel):
    """OCR 분석 이력 목록."""

    items: list[AiOcrAnalysisHistoryItem] = Field(default_factory=list)


class AiOcrAnalysisHistoryDeleteRequest(BaseModel):
    """OCR 분석 이력 일괄 삭제 요청."""

    ids: list[int] = Field(min_length=1)


class AiOcrAnalysisHistoryDeleteResponse(BaseModel):
    """OCR 분석 이력 일괄 삭제 결과."""

    deleted_count: int = Field(ge=0)


class AiOcrCreateArticleRequest(BaseModel):
    """Zendesk 아티클 생성 요청."""

    instance_id: int
    brand_id: int
    section_a_id: int
    title: str = Field(min_length=1, max_length=500)
    html_body: str = Field(min_length=1)
    label_names: list[str] = Field(default_factory=list)
    locale: str = Field(default="ko", max_length=20)
    draft: bool = False


class AiOcrCreateArticleResponse(BaseModel):
    """Zendesk 아티클 생성 결과."""

    article_id: int
    html_url: str | None = None
    section_a_id: int
    section_name: str
    logs: list[AiOcrLogEntryResponse] = Field(default_factory=list)


class ImageConvertArticleItem(BaseModel):
    """이미지 포함 소스 아티클 목록 항목."""

    id: int
    a_id: int
    title: str
    html_url: str | None = None
    section_name: str
    image_count: int
    label_names: list[str] = Field(default_factory=list)


class ImageConvertArticleListResponse(BaseModel):
    """이미지 포함 소스 아티클 목록."""

    items: list[ImageConvertArticleItem] = Field(default_factory=list)


class ImageConvertArticleImageItem(BaseModel):
    """아티클 본문 이미지 한 건."""

    index: int
    source_url: str
    filename: str
    availability: str = Field(
        default="unknown",
        description="ok=API 다운로드 가능, external_paste=타 Zendesk 붙여넣기, unknown=미확인",
    )
    availability_reason: str | None = None


class ImageConvertArticleDetailResponse(BaseModel):
    """소스 아티클 상세."""

    id: int
    a_id: int
    title: str
    html_url: str | None = None
    section_name: str
    label_names: list[str] = Field(default_factory=list)
    body: str | None = None
    images: list[ImageConvertArticleImageItem] = Field(default_factory=list)
    brand_subdomain: str


class ImageConvertAnalyzeRequest(BaseModel):
    """소스 아티클 OCR 변환 요청."""

    source_instance_id: int
    article_id: int


class ImageConvertImagePreviewItem(BaseModel):
    """OCR 분석에 사용된 이미지 미리보기."""

    index: int
    filename: str
    preview_data_url: str


class ImageConvertAnalyzeResponse(BaseModel):
    """소스 아티클 OCR 변환 결과."""

    history_id: int
    source_article_id: int
    source_article_a_id: int
    source_article_title: str
    title: str
    html_body: str
    label_names: list[str] = Field(default_factory=list)
    detected_product: str
    maintenance_cycle: str | None = None
    body_preview_text: str
    image_count: int
    ocr_image_count: int
    image_previews: list[ImageConvertImagePreviewItem] = Field(default_factory=list)
    logs: list[AiOcrLogEntryResponse] = Field(default_factory=list)


FetchDetailSectionResponse.model_rebuild()


class ZendeskApiOperationResponse(BaseModel):
    """Zendesk API 카탈로그 operation 한 건."""

    id: str
    category: str
    group: str
    label: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path_template: str
    path_params: list[str] = Field(default_factory=list)
    doc_url: str
    sample_body: dict[str, Any] | None = None
    default_query: dict[str, str] | None = None


class ZendeskApiGroupResponse(BaseModel):
    """Zendesk API 카탈로그 중분류."""

    id: str
    label: str
    operations: list[ZendeskApiOperationResponse] = Field(default_factory=list)


class ZendeskApiCategoryResponse(BaseModel):
    """Zendesk API 카탈로그 대분류."""

    id: str
    label: str
    groups: list[ZendeskApiGroupResponse] = Field(default_factory=list)


class ZendeskApiProductResponse(BaseModel):
    """Zendesk API capability 영역."""

    id: str
    label: str
    doc_url: str
    categories: list[ZendeskApiCategoryResponse] = Field(default_factory=list)


class ZendeskApiCatalogResponse(BaseModel):
    """GET /zendesk-proxy/catalog 응답."""

    products: list[ZendeskApiProductResponse] = Field(default_factory=list)


# 하위 호환 alias
ZendeskTicketingApiOperationResponse = ZendeskApiOperationResponse
ZendeskTicketingApiGroupResponse = ZendeskApiGroupResponse
ZendeskTicketingApiCategoryResponse = ZendeskApiCategoryResponse
ZendeskTicketingApiCatalogResponse = ZendeskApiCatalogResponse


class ZendeskProxyRequest(BaseModel):
    """Zendesk API 프록시 요청."""

    instance_id: int
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str = Field(min_length=1, max_length=500)
    json_body: dict[str, Any] | None = None
    raw_body: str | None = None
    query_params: dict[str, str] | None = None
    request_headers: dict[str, str] | None = None


class ZendeskProxyResponse(BaseModel):
    """Zendesk API 프록시 응답."""

    success: bool
    http_status: int
    latency_ms: int
    request_url: str
    response_body: Any = None
    response_headers: dict[str, str] = Field(default_factory=dict)
    error_message: str | None = None
