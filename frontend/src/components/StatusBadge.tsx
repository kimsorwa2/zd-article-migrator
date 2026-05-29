interface StatusBadgeProps {
  active: boolean;
}

export default function StatusBadge({ active }: StatusBadgeProps) {
  return <span className={`badge ${active ? "badge-green" : "badge-gray"}`}>{active ? "활성" : "비활성"}</span>;
}
