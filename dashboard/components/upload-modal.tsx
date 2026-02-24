"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { mutate } from "swr";

type RunMode = "mock" | "live" | "hybrid";

const MODE_OPTIONS: { value: RunMode; label: string; description: string }[] = [
  { value: "live", label: "Live", description: "Real Devin sessions" },
  { value: "mock", label: "Mock", description: "Simulated sessions" },
  { value: "hybrid", label: "Hybrid", description: "Live for connected repos, mock for others" },
];

function ModeDropdown({
  mode,
  onChange,
}: {
  mode: RunMode;
  onChange: (m: RunMode) => void;
}) {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const selected = MODE_OPTIONS.find((o) => o.value === mode) ?? MODE_OPTIONS[0];

  return (
    <div>
      <label className="block text-sm font-medium text-foreground mb-2">
        Mode
      </label>
      <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground hover:bg-accent transition-colors"
        >
          <span>{selected.label}</span>
          <svg
            width="14"
            height="14"
            viewBox="0 0 14 14"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
          >
            <polyline points="3.5 5.5 7 9 10.5 5.5" />
          </svg>
        </button>

        {open && (
          <div className="absolute z-10 mt-1 w-full rounded-md border border-border bg-card shadow-lg overflow-hidden">
            {MODE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
                className={`flex w-full items-start gap-3 px-3 py-2.5 text-left text-sm transition-colors ${
                  mode === opt.value
                    ? "bg-accent text-foreground"
                    : "text-foreground hover:bg-accent/50"
                }`}
              >
                {/* Check icon for selected */}
                <span className="mt-0.5 w-4 shrink-0">
                  {mode === opt.value && (
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 14 14"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="3 7 5.5 9.5 11 4" />
                    </svg>
                  )}
                </span>
                <div>
                  <p className="font-medium">{opt.label}</p>
                  <p className="text-xs text-muted-foreground">
                    {opt.description}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface UploadModalProps {
  open: boolean;
  onClose: () => void;
}

export function UploadModal({ open, onClose }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [waveSize, setWaveSize] = useState(5);
  const [mode, setMode] = useState<"mock" | "live" | "hybrid">("live");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetState = useCallback(() => {
    setFile(null);
    setWaveSize(5);
    setMode("live");
    setError(null);
    setUploading(false);
    setDragOver(false);
  }, []);

  const handleClose = useCallback(() => {
    resetState();
    onClose();
  }, [onClose, resetState]);

  const validateFile = useCallback((f: File): string | null => {
    if (!f.name.toLowerCase().endsWith(".csv")) {
      return "File must be a .csv file";
    }
    if (f.size > 10 * 1024 * 1024) {
      return "File exceeds maximum size of 10MB";
    }
    return null;
  }, []);

  const handleFileSelect = useCallback(
    (f: File) => {
      const validationError = validateFile(f);
      if (validationError) {
        setError(validationError);
        setFile(null);
        return;
      }
      setError(null);
      setFile(f);
    },
    [validateFile],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(false);

      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) {
        handleFileSelect(droppedFile);
      }
    },
    [handleFileSelect],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0];
      if (selectedFile) {
        handleFileSelect(selectedFile);
      }
    },
    [handleFileSelect],
  );

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("wave_size", String(waveSize));
    formData.append("mode", mode);

    try {
      const res = await fetch("/api/runs", { method: "POST", body: formData });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Upload failed");
      }
      // Refresh run list across all components
      await mutate("/api/runs");
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={handleClose}
    >
      <div
        className="w-full max-w-lg rounded-lg border border-border bg-card shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="font-serif text-xl font-semibold text-foreground">
            New Remediation Run
          </h2>
          <button
            onClick={handleClose}
            className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 18 18"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="4" y1="4" x2="14" y2="14" />
              <line x1="14" y1="4" x2="4" y2="14" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          {/* Drop zone */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              CSV File
            </label>
            <div
              className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors cursor-pointer ${
                dragOver
                  ? "border-primary bg-accent/50"
                  : file
                    ? "border-primary/50 bg-accent/30"
                    : "border-border hover:border-muted-foreground"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleInputChange}
                className="hidden"
              />
              {file ? (
                <div className="text-center">
                  <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="mx-auto mb-2 text-primary"
                  >
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                  <p className="text-sm font-medium text-foreground">
                    {file.name}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              ) : (
                <div className="text-center">
                  <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="mx-auto mb-2 text-muted-foreground"
                  >
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  <p className="text-sm text-muted-foreground">
                    Drag & drop a CSV file, or{" "}
                    <span className="text-foreground font-medium">browse</span>
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Max 10MB, up to 5,000 rows
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Mode + Wave size — same row */}
          <div className="grid grid-cols-2 gap-4">
            <ModeDropdown mode={mode} onChange={setMode} />

            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Wave Size
              </label>
              <div className="inline-flex items-center rounded-md border border-border bg-background w-fit">
                <button
                  type="button"
                  onClick={() => setWaveSize((v) => Math.max(1, v - 1))}
                  className="flex items-center justify-center w-8 h-8 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors rounded-l-md"
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                    <line x1="3" y1="6" x2="9" y2="6" />
                  </svg>
                </button>
                <input
                  type="text"
                  inputMode="numeric"
                  value={waveSize}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10);
                    if (!isNaN(val) && val >= 1 && val <= 100) {
                      setWaveSize(val);
                    }
                  }}
                  className="w-12 h-8 border-x border-border bg-background text-center text-sm text-foreground focus:outline-none [appearance:textfield]"
                />
                <button
                  type="button"
                  onClick={() => setWaveSize((v) => Math.min(100, v + 1))}
                  className="flex items-center justify-center w-8 h-8 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors rounded-r-md"
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                    <line x1="6" y1="3" x2="6" y2="9" />
                    <line x1="3" y1="6" x2="9" y2="6" />
                  </svg>
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-1.5">
                findings per wave (1–100)
              </p>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
          <button
            onClick={handleClose}
            disabled={uploading}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {uploading ? (
              <>
                <svg
                  className="animate-spin h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Starting...
              </>
            ) : (
              "Start Run"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
