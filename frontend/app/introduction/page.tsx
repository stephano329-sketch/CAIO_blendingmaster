"use client";

import Link from "next/link";

const STAGES: { label: string; icon: string; highlight?: boolean }[] = [
  { label: "원유 투입", icon: "ti-droplet" },
  { label: "원유 증류", icon: "ti-flame" },
  { label: "경유 반제품\n불순물 제거", icon: "ti-filter" },
  { label: "경유 반제품 배합", icon: "ti-test-pipe", highlight: true },
  { label: "첨가제 주입", icon: "ti-vaccine", highlight: true },
  { label: "출하", icon: "ti-truck-delivery" },
];

export default function IntroductionPage() {
  return (
    <>
      <div className="card" style={{ padding: "20px 24px", marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: 8,
              background: "#BA7517",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontWeight: 600,
              fontSize: 18,
            }}
          >
            B
          </div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text-primary)" }}>
              Blending Master
            </div>
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
              경유 저온성상과 WAFI 주입량 의사결정을 지원하는 전문가 지식 기반 AI Agent
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: "20px 24px", marginBottom: 16 }}>
        <div className="card-title" style={{ fontSize: 14, marginBottom: 12, color: "var(--color-text-primary)" }}>
          배경
        </div>
        <div style={{ fontSize: 13, color: "var(--color-text-primary)", lineHeight: 1.7 }}>
          동절기·혹한기에는 경유의 저온성상(CFPP/CP/PP)이 규격에 미달하면 재블렌딩 손실이
          발생하고, 이를 피하려고 WAFI 첨가제를 과다 투입하면 첨가제 비용이 누적됩니다.
          이 판단은 베테랑 연구원의 경험에 크게 의존해 왔으나, 핵심 인력의 정년 도달이
          가까워 지식 휘발 위험이 큽니다.
        </div>
      </div>

      <div className="card" style={{ padding: "20px 24px", marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 14 }}>
          <i className="ti ti-alert-triangle" style={{ fontSize: 16, color: "#C0392B" }} />
          <div className="card-title" style={{ fontSize: 14, color: "var(--color-text-primary)", margin: 0 }}>
            Pain Points
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 }}>
          {[
            {
              icon: "ti-refresh-alert",
              title: "재블렌딩 손실",
              desc: "규격 미달 시 재작업으로 시간·비용 손실 발생",
            },
            {
              icon: "ti-currency-won",
              title: "WAFI 과투입 비용",
              desc: "안전 마진 확보를 위한 과다 주입으로 첨가제 비용 누적",
            },
            {
              icon: "ti-arrows-shuffle",
              title: "판단 편차",
              desc: "연구원별 경험 차이로 동일 조건에서도 결정이 달라짐",
            },
            {
              icon: "ti-user-off",
              title: "노하우 단절 위험",
              desc: "베테랑 퇴직 시 의사결정 기준 재구성 어려움",
            },
          ].map((it) => (
            <div
              key={it.title}
              style={{
                display: "flex",
                gap: 10,
                padding: "10px 12px",
                border: "1px solid #E5B8B8",
                background: "#FDF2F2",
                borderRadius: 6,
              }}
            >
              <i className={`ti ${it.icon}`} style={{ fontSize: 18, color: "#C0392B", marginTop: 2 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#922B21" }}>{it.title}</div>
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 2, lineHeight: 1.5 }}>
                  {it.desc}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card" style={{ padding: "20px 24px", marginBottom: 16 }}>
        <div className="card-title" style={{ fontSize: 14, marginBottom: 12, color: "var(--color-text-primary)" }}>
          목적
        </div>
        <div style={{ fontSize: 13, color: "var(--color-text-primary)", lineHeight: 1.7 }}>
          베테랑의 판단 기준을 구조화·검색 가능한 지식으로 전환하고, 저연차 연구원이
          반제품 성상·블렌딩 비율·계절·탱크 이력을 기반으로 빠르고 일관된 WAFI 주입량
          의사결정을 내릴 수 있도록 ML 예측, RAG 검색, 경험치 DB를 통합 제공합니다.
        </div>
      </div>

      <div className="card" style={{ padding: "20px 24px", marginBottom: 16 }}>
        <div className="card-title" style={{ fontSize: 14, marginBottom: 4, color: "var(--color-text-primary)" }}>
          경유 제품 출하 Block Diagram
        </div>
        <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginBottom: 18 }}>
          본 시스템은 <strong style={{ color: "#BA7517" }}>경유 전문가 경험 및 노하우를 학습</strong>하여{" "}
          <strong style={{ color: "#BA7517" }}>경유 반제품 배합</strong> 및{" "}
          <strong style={{ color: "#BA7517" }}>첨가제 주입</strong> 단계의 의사결정을 지원합니다.
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "stretch",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 8,
          }}
        >
          {(() => {
            const renderStage = (s: typeof STAGES[number]) => (
              <div
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "14px 8px",
                  borderRadius: 8,
                  border: s.highlight ? "1.5px solid #BA7517" : "0.5px solid var(--color-border-secondary)",
                  background: s.highlight ? "#FAEEDA" : "var(--color-background-primary)",
                  minHeight: 90,
                }}
              >
                <i
                  className={`ti ${s.icon}`}
                  style={{
                    fontSize: 22,
                    color: s.highlight ? "#BA7517" : "#185FA5",
                    marginBottom: 6,
                  }}
                />
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: s.highlight ? 600 : 500,
                    color: s.highlight ? "#854F0B" : "var(--color-text-primary)",
                    textAlign: "center",
                    whiteSpace: "pre-line",
                    lineHeight: 1.3,
                  }}
                >
                  {s.label}
                </div>
              </div>
            );
            const chevron = (
              <i
                className="ti ti-chevron-right"
                style={{ fontSize: 18, color: "var(--color-text-secondary)", flexShrink: 0 }}
              />
            );

            const nodes: React.ReactNode[] = [];
            for (let i = 0; i < STAGES.length; i++) {
              const s = STAGES[i];
              if (s.highlight && STAGES[i + 1]?.highlight) {
                // Group consecutive highlighted stages under "AI 의사결정 지원"
                const next = STAGES[i + 1];
                nodes.push(
                  <div
                    key="ai-group"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      flex: "2 1 0",
                      minWidth: 260,
                      gap: 4,
                    }}
                  >
                    <div
                      style={{
                        flex: 1,
                        border: "1.5px dashed #BA7517",
                        borderRadius: 10,
                        padding: "16px 8px 10px",
                        background: "rgba(186, 117, 23, 0.04)",
                        position: "relative",
                      }}
                    >
                      <div
                        style={{
                          position: "absolute",
                          top: -10,
                          left: "50%",
                          transform: "translateX(-50%)",
                          background: "#BA7517",
                          color: "#fff",
                          fontSize: 11,
                          fontWeight: 600,
                          padding: "2px 10px",
                          borderRadius: 10,
                          whiteSpace: "nowrap",
                        }}
                      >
                        AI 의사결정 지원
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        {renderStage(s)}
                        {chevron}
                        {renderStage(next)}
                      </div>
                    </div>
                    {i + 1 < STAGES.length - 1 && chevron}
                  </div>
                );
                i += 1; // skip next, consumed in group
                continue;
              }
              nodes.push(
                <div
                  key={s.label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    flex: "1 1 0",
                    minWidth: 120,
                    gap: 4,
                  }}
                >
                  {renderStage(s)}
                  {i < STAGES.length - 1 && chevron}
                </div>
              );
            }
            return nodes;
          })()}
        </div>
      </div>

      <div className="card" style={{ padding: "20px 24px" }}>
        <div className="card-title" style={{ fontSize: 14, marginBottom: 12, color: "var(--color-text-primary)" }}>
          주요 기능
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 }}>
          {[
            { href: "/judge", icon: "ti-clipboard-check", title: "신규 판단", desc: "반제품 구성 + 성상으로 WAFI 시나리오 3개 추천" },
            { href: "/consult", icon: "ti-message-dots", title: "AI 상담", desc: "RAG + LLM 기반 자연어 상담" },
            { href: "/journal", icon: "ti-book-2", title: "제품 배합 일지", desc: "사용자가 채택한 batch 영속 + 실측 입력" },
            { href: "/interview", icon: "ti-user-question", title: "지식 추출", desc: "베테랑 판단 기준 Q1~Q5 수집" },
            { href: "/kb", icon: "ti-database", title: "경험치 DB", desc: "수집된 판단 기준 카드 조회" },
            { href: "/rag", icon: "ti-file-search", title: "RAG 문서 확인", desc: "인덱싱된 219건 문서 검색" },
          ].map((f) => (
            <Link
              key={f.href}
              href={f.href}
              style={{
                display: "flex",
                gap: 10,
                padding: "10px 12px",
                border: "0.5px solid var(--color-border-tertiary)",
                borderRadius: 6,
                textDecoration: "none",
                background: "var(--color-background-primary)",
                transition: "border-color 0.15s, background 0.15s",
              }}
            >
              <i className={`ti ${f.icon}`} style={{ fontSize: 18, color: "#BA7517", marginTop: 2 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)" }}>
                  {f.title}
                </div>
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 2 }}>
                  {f.desc}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}
