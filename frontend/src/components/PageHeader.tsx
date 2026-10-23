import { ReactNode } from "react";
import { Loader2 } from "lucide-react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  backLink?: string;
  loading?: boolean;
}

export function PageHeader({
  title,
  subtitle,
  action,
  backLink,
  loading = false,
}: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          {backLink && (
            <a href={backLink} className="btn btn-ghost btn-sm">
              ← Back
            </a>
          )}
          <div>
            <h1 className="page-title">{loading ? (
              <>
                <Loader2 size={24} className="animate-spin" style={{ color: "var(--color-primary)" }} />
              </>
            ) : (
              title
            )}</h1>
            {subtitle && <p className="page-subtitle">{subtitle}</p>}
          </div>
        </div>
        {action}
      </div>
    </header>
  );
}