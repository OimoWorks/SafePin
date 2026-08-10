export default function Attribution() {
  return (
    <div className="absolute bottom-0 left-0 z-[1000] bg-white/80 text-gray-500 text-[10px] leading-tight px-2 py-1 rounded-tr-lg max-w-[240px]">
      本アプリは
      <a
        href="https://www.city.matsuyama.ehime.jp/shisei/opendata/"
        target="_blank"
        rel="noopener noreferrer"
        className="underline"
      >
        松山市オープンデータ
      </a>
      を加工して作成（CC BY 4.0）
    </div>
  )
}
