import { BrandMark } from '../components/brand-mark'
import { startInstall } from '../store'

export default function Welcome() {
  return (
    <main className="hermes-fade-in flex h-full items-center justify-center overflow-y-auto px-6 py-6" lang="ja">
      <div className="grid w-full max-w-[42rem] items-center gap-6 overflow-hidden rounded-2xl border border-white/10 bg-[#101a2c] p-6 text-white shadow-2xl sm:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] sm:p-8">
        <div className="flex justify-center rounded-xl bg-[#e9dfce] p-3 sm:p-4">
          <BrandMark className="size-28 sm:size-full sm:aspect-square" />
        </div>
        <div className="min-w-0">
          <h1 aria-label="ALL AI5.2 TACT" className="m-0 text-4xl leading-none font-semibold tracking-tight sm:text-5xl">
            TACT
            <span className="mt-2 block text-sm font-medium tracking-normal text-[#e3b67c]">ALL AI5.2</span>
          </h1>
          <p className="mt-4 mb-0 text-sm leading-relaxed text-white/75">
            このコンピューターに TACT Desktop をセットアップします。インストールには数分かかります。
          </p>
          <button
            className="mt-5 cursor-pointer rounded-lg bg-[#f5c58d] px-4 py-2.5 text-sm font-semibold text-[#101a2c] transition-colors hover:bg-[#ffddb4] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white"
            onClick={() => void startInstall()}
            type="button"
          >
            インストール
          </button>
        </div>
      </div>
    </main>
  )
}
