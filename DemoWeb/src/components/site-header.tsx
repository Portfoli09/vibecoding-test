import Link from "next/link";
import { MessageSquareTextIcon, PenLineIcon } from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { buttonVariants } from "@/components/ui/button";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-backdrop-filter:bg-background/60">
      <div className="mx-auto flex h-14 w-full max-w-4xl items-center justify-between gap-2 px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <MessageSquareTextIcon className="size-5" />
          <span>DemoWeb 게시판</span>
        </Link>
        <div className="flex items-center gap-1">
          <Link href="/posts/new" className={buttonVariants({ size: "sm" })}>
            <PenLineIcon />
            <span className="hidden sm:inline">글쓰기</span>
          </Link>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
