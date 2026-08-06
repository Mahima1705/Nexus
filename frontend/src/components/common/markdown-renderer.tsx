"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark, oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils/cn";

export function MarkdownRenderer({ content, className }: { content: string; className?: string }) {
  const { resolvedTheme } = useTheme();
  const codeStyle = resolvedTheme === "dark" ? oneDark : oneLight;

  return (
    <div
      className={cn(
        "prose prose-sm max-w-none dark:prose-invert",
        "prose-headings:font-semibold prose-p:leading-relaxed",
        "prose-pre:bg-transparent prose-pre:p-0",
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className: codeClassName, children, ...props }) {
            const match = /language-(\w+)/.exec(codeClassName ?? "");
            const isInline = !codeClassName;
            const text = String(children).replace(/\n$/, "");

            if (isInline) {
              return (
                <code className="rounded bg-muted px-1.5 py-0.5 text-sm" {...props}>
                  {children}
                </code>
              );
            }

            return (
              <SyntaxHighlighter
                style={codeStyle}
                language={match?.[1] ?? "text"}
                PreTag="div"
                customStyle={{ borderRadius: "0.5rem", fontSize: "0.8125rem", margin: 0 }}
              >
                {text}
              </SyntaxHighlighter>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
