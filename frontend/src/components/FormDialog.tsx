import { ReactNode } from "react";
import { X, Save, Loader2 } from "lucide-react";

interface FormDialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  submitLabel?: string;
  isSubmitting?: boolean;
  onSubmit?: (e: React.FormEvent) => void;
}

export function FormDialog({
  isOpen,
  onClose,
  title,
  children,
  submitLabel = "Save",
  isSubmitting = false,
  onSubmit,
}: FormDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="card mb-6">
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="card-title">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="btn btn-ghost btn-sm"
            aria-label="Close dialog"
          >
            <X size={16} />
          </button>
        </div>

        {children}

        <div className="flex justify-end gap-2 pt-4 border-t border-[var(--color-border)]">
          <button type="button" onClick={onClose} className="btn btn-secondary">
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Saving...
              </>
            ) : (
              <>
                <Save size={16} /> {submitLabel}
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}