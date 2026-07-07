export default function Logo({ size = 36 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 512 512"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="234" y="234" width="214" height="214" rx="48" fill="#ECEEF2" />
      <text
        x="341"
        y="392"
        textAnchor="middle"
        fontFamily="Arial, Helvetica, sans-serif"
        fontSize="150"
        fontWeight="700"
        fill="#3B4453"
      >
        A
      </text>
      <rect x="64" y="64" width="224" height="224" rx="52" fill="#2F80ED" />
      <text
        x="176"
        y="236"
        textAnchor="middle"
        fontFamily="'Noto Sans SC','Noto Sans JP','Malgun Gothic','Microsoft YaHei',sans-serif"
        fontSize="170"
        fontWeight="700"
        fill="#FFFFFF"
      >
        文
      </text>
      <g
        stroke="#2F80ED"
        strokeWidth="22"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      >
        <path d="M300 96 C 372 78 432 104 434 172" />
        <path d="M412 152 L434 178 L456 152" />
        <path d="M212 416 C 140 434 80 408 78 340" />
        <path d="M56 360 L78 334 L100 360" />
      </g>
    </svg>
  );
}
