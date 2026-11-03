import Link from "next/link";
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const WINDOW = 5;

function href(page: number) {
  return page <= 1 ? "/" : `/?page=${page}`;
}

export function PostPagination({
  page,
  totalPages,
}: {
  page: number;
  totalPages: number;
}) {
  if (totalPages <= 1) return null;

  const start = Math.max(1, Math.min(page - Math.floor(WINDOW / 2), totalPages - WINDOW + 1));
  const end = Math.min(totalPages, start + WINDOW - 1);
  const pages = Array.from({ length: end - start + 1 }, (_, i) => start + i);
  const navClass = buttonVariants({ variant: "ghost", size: "sm" });
  const disabledClass = "pointer-events-none opacity-50";

  return (
    <nav aria-label="페이지 이동" className="flex items-center justify-center gap-1">
      <Link
        href={href(page - 1)}
        aria-disabled={page === 1}
        tabIndex={page === 1 ? -1 : undefined}
        className={cn(navClass, page === 1 && disabledClass)}
      >
        <ChevronLeftIcon />
        <span className="hidden sm:inline">이전</span>
      </Link>
      {pages.map((p) => (
        <Link
          key={p}
          href={href(p)}
          aria-current={p === page ? "page" : undefined}
          className={buttonVariants({
            variant: p === page ? "outline" : "ghost",
            size: "icon-sm",
          })}
        >
          {p}
        </Link>
      ))}
      <Link
        href={href(page + 1)}
        aria-disabled={page === totalPages}
        tabIndex={page === totalPages ? -1 : undefined}
        className={cn(navClass, page === totalPages && disabledClass)}
      >
        <span className="hidden sm:inline">다음</span>
        <ChevronRightIcon />
      </Link>
    </nav>
  );
}
