import { useEffect, useState } from "react";
import { Clapperboard, Film } from "lucide-react";
import { WizardState } from "@/store/wizardStore";
import { ProcessingScreen } from "@/components/ProcessingScreen";

const RESET_GENERATION_STATE = {
  generatedVideo: null,
  styledVideoUrl: "",
  styledVideoPath: "",
  subtitleSource: "disabled" as const,
  generationStatus: "idle" as const,
  generationPhase: "",
  generationProgress: null,
  generationError: "",
};

const RATIOS = ["16:9", "9:16", "1:1"];

function getAliveProgressCap(progress: number): number {
  if (progress >= 100) return 100;
  if (progress >= 93) return 99;
  if (progress >= 86) return 98;
  if (progress >= 75) return 94;
  if (progress >= 48) return 84;
  if (progress >= 35) return 64;
  if (progress >= 20) return 44;
  return 28;
}

interface StepPreviewProps {
  state: WizardState;
  update: (partial: Partial<WizardState>) => void;
}

export function StepPreview({ state, update }: StepPreviewProps) {
  const activeTranscript = state.videoType === "remotion" ? state.remotionTranscript : state.transcript;
  const isRemotion = state.videoType === "remotion";
  const isHybrid = state.videoType === "hybrid_remotion_avatar_pip";
  const statusLabel = getGenerationStatusLabel(state.generationStatus, isRemotion);
  const avatarName =
    isRemotion
      ? "Text to Video"
      : isHybrid
        ? state.avatarName || state.avatarId || "Hybrid Avatar"
      : state.avatarName || state.avatarId || "None";
  const wordCount = activeTranscript.trim() ? activeTranscript.trim().split(/\s+/).length : 0;
  const duration = `~${Math.max(1, Math.round(wordCount / 130))} min`;
  const generatedVideo = state.generatedVideo;
  const previewUrl = state.styledVideoUrl || generatedVideo?.video_url || "";
  const isProcessing = state.generationStatus === "submitting" || state.generationStatus === "styling";
  const estimatedMinutes = isRemotion ? 5 : Math.max(2, Math.round(wordCount / 130) * 2);
  const estimatedSeconds =
    state.generationStatus === "styling"
      ? 15
      : estimatedMinutes * 60;
  const [phaseStartedAt, setPhaseStartedAt] = useState<number | null>(null);
  const [phaseProgress, setPhaseProgress] = useState(0);
  const [smoothProgress, setSmoothProgress] = useState(0);
  const [aliveTargetProgress, setAliveTargetProgress] = useState(0);
  const hasBackendProgress = typeof state.generationProgress === "number";
  const targetProgress = hasBackendProgress ? aliveTargetProgress : phaseProgress;
  const displayProgress = Math.min(100, Math.max(0, smoothProgress));
  const progressLabel = Math.max(1, Math.round(displayProgress));
  const phaseLabel =
    state.generationPhase ||
    (hasBackendProgress ? "Processing" : `Estimated time: ${estimatedSeconds >= 60 ? `~${Math.round(estimatedSeconds / 60)} min` : `~${estimatedSeconds}s`}`);
  const progressSourceLabel = hasBackendProgress ? "Live job status" : "Estimated progress";
  const checkpoints = [
    { label: "Queued", value: 5 },
    { label: "Generate", value: 35 },
    { label: "Render", value: 55 },
    { label: "Upload", value: 86 },
    { label: "Ready", value: 100 },
  ];

  useEffect(() => {
    if (!isProcessing) {
      setPhaseStartedAt(null);
      setPhaseProgress(0);
      setSmoothProgress(0);
      setAliveTargetProgress(0);
      return;
    }

    setPhaseStartedAt(Date.now());
  }, [isProcessing, state.generationStatus]);

  useEffect(() => {
    if (!isProcessing || phaseStartedAt === null) {
      return;
    }

    const tick = () => {
      const elapsedMs = Date.now() - phaseStartedAt;
      if (state.generationStatus === "styling") {
        const stylingProgress = Math.min(97, 88 + (elapsedMs / 45000) * 9);
        setPhaseProgress(stylingProgress);
        return;
      }

      const targetDurationMs = estimatedMinutes * 60 * 1000;
      const progressCap = isRemotion ? 96 : 88;
      const settleWindowMs = isRemotion ? 2 * 60 * 1000 : 0;
      const initialCap = isRemotion ? 90 : progressCap;
      const initialProgress = Math.min(initialCap, (elapsedMs / targetDurationMs) * initialCap);
      const overflowMs = Math.max(0, elapsedMs - targetDurationMs);
      const overflowProgress =
        isRemotion && settleWindowMs > 0
          ? Math.min(progressCap - initialCap, (overflowMs / settleWindowMs) * (progressCap - initialCap))
          : 0;
      const submittingProgress = Math.min(progressCap, initialProgress + overflowProgress);
      setPhaseProgress(submittingProgress);
    };

    tick();
    const intervalId = window.setInterval(tick, 500);
    return () => window.clearInterval(intervalId);
  }, [estimatedMinutes, isProcessing, isRemotion, phaseStartedAt, state.generationStatus]);

  useEffect(() => {
    if (!isProcessing || !hasBackendProgress) {
      return;
    }

    setAliveTargetProgress((current) => Math.max(current, state.generationProgress ?? 0));
  }, [hasBackendProgress, isProcessing, state.generationProgress]);

  useEffect(() => {
    if (!isProcessing || !hasBackendProgress || state.generationStatus === "failed") {
      return;
    }

    const intervalId = window.setInterval(() => {
      setAliveTargetProgress((current) => {
        const backendProgress = state.generationProgress ?? 0;
        const floor = Math.max(current, backendProgress);
        const cap = getAliveProgressCap(backendProgress);
        if (floor >= cap) {
          return floor;
        }
        const increment = floor < 45 ? 0.45 : floor < 84 ? 0.28 : 0.14;
        return Math.min(cap, floor + increment);
      });
    }, 700);

    return () => window.clearInterval(intervalId);
  }, [hasBackendProgress, isProcessing, state.generationProgress, state.generationStatus]);

  useEffect(() => {
    if (!isProcessing) {
      return;
    }

    let animationFrameId = 0;
    const animate = () => {
      let shouldContinue = true;
      setSmoothProgress((current) => {
        const nextTarget = Math.min(100, Math.max(0, targetProgress));
        const gap = nextTarget - current;
        if (Math.abs(gap) < 0.08) {
          shouldContinue = false;
          return nextTarget;
        }
        return current + gap * 0.08;
      });
      if (shouldContinue) {
        animationFrameId = window.requestAnimationFrame(animate);
      }
    };

    animationFrameId = window.requestAnimationFrame(animate);
    return () => window.cancelAnimationFrame(animationFrameId);
  }, [isProcessing, targetProgress]);

  return (
    <div className="flex gap-8 max-w-5xl">
      {/* Main preview */}
      <div className="flex-1 space-y-4">
        <div className="flex gap-2">
          {RATIOS.map((r) => (
            <button
              key={r}
              disabled={isProcessing}
              onClick={() => update({ aspectRatio: r, ...RESET_GENERATION_STATE })}
              className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all ${state.aspectRatio === r
                  ? "border-primary bg-primary/10 text-foreground"
                  : "border-border bg-secondary text-muted-foreground hover:text-foreground"
                } disabled:cursor-not-allowed disabled:opacity-50`}
            >
              {r}
            </button>
          ))}
        </div>

        <div
          className={`relative rounded-xl bg-background border border-border flex items-center justify-center overflow-hidden ${state.aspectRatio === "16:9"
              ? "aspect-video"
              : state.aspectRatio === "9:16"
                ? "aspect-[9/16] max-h-[420px]"
                : "aspect-square max-h-[420px]"
            }`}
        >
          {isProcessing ? (
            <ProcessingScreen
              status={state.generationStatus}
              estimatedTime={estimatedMinutes.toString()}
              isLongVideo={wordCount > 300}
              videoType={state.videoType}
            />
          ) : previewUrl ? (
            <video
              key={previewUrl}
              controls
              src={previewUrl}
              poster={generatedVideo?.thumbnail_url ?? undefined}
              preload="metadata"
              playsInline
              className={`w-full h-full ${state.videoType === "avatar" ? "object-cover" : "object-contain bg-black"}`}
            />
          ) : generatedVideo?.thumbnail_url ? (
            <img
              src={generatedVideo.thumbnail_url}
              alt={generatedVideo.title ?? "Generated video preview"}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="text-center">
              <div className="w-20 h-20 rounded-[2rem] bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-4">
                {isRemotion
                  ? <Film className="h-9 w-9 text-primary opacity-70" />
                  : <Clapperboard className="h-9 w-9 text-primary opacity-70" />}
              </div>
              <p className="text-sm text-muted-foreground">
                {isRemotion
                  ? "Generate the Text Video below to preview the multi-scene output here."
                  : "Generate the video to preview it here."}
              </p>
            </div>
          )}
        </div>

        {state.generationStatus === "failed" && state.generationError ? (
          <div className="rounded-xl border border-destructive/25 bg-destructive/5 px-5 py-4">
            <p className="text-sm font-semibold text-foreground">Generation failed</p>
            <p className="mt-1 text-sm text-muted-foreground">{state.generationError}</p>
          </div>
        ) : null}

        {isProcessing ? (
          <div className="rounded-xl border border-border bg-card/80 px-5 py-4 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">
                  {isRemotion ? "Text to Video Progress" : "Generation Progress"}
                </p>
                <p className="mt-1 truncate text-sm font-semibold text-foreground">{phaseLabel}</p>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-2xl font-semibold tabular-nums text-foreground">{progressLabel}%</p>
                <p className="text-[11px] font-medium text-muted-foreground">{progressSourceLabel}</p>
              </div>
            </div>

            <div className="relative mt-4 h-4 overflow-hidden rounded-full border border-border/70 bg-secondary shadow-inner">
              <div
                className="relative h-full overflow-hidden rounded-full bg-gradient-to-r from-primary/75 via-primary to-primary/75 shadow-[0_0_18px_rgba(95,18,132,0.24)] transition-[width] duration-300 ease-out"
                style={{ width: `${Math.min(100, Math.max(0, displayProgress))}%` }}
              >
                <div className="absolute inset-0 bg-[linear-gradient(110deg,transparent_0%,rgba(255,255,255,0.45)_40%,transparent_78%)] animate-[progress-shimmer_1.5s_linear_infinite]" />
              </div>
            </div>

            <div className="mt-3 grid grid-cols-5 gap-2">
              {checkpoints.map((checkpoint) => {
                const isDone = displayProgress >= checkpoint.value - 0.5;
                return (
                  <div key={checkpoint.label} className="min-w-0">
                    <div className={`mx-auto h-2 w-2 rounded-full transition-colors ${isDone ? "bg-primary" : "bg-border"}`} />
                    <p className={`mt-1 truncate text-center text-[10px] font-medium ${isDone ? "text-foreground" : "text-muted-foreground"}`}>
                      {checkpoint.label}
                    </p>
                  </div>
                );
              })}
            </div>

            <style>{`
              @keyframes progress-shimmer {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
              }
            `}</style>
          </div>
        ) : null}
      </div>

      {/* Summary */}
      <div className="w-64 shrink-0">
        <div className="surface-card p-5 space-y-4">
          <h3 className="text-sm font-semibold text-foreground">Video Summary</h3>
          <SummaryRow label="Style" value={isRemotion ? "Text to Video" : isHybrid ? "VisionDesk" : "Avatar"} />
          <SummaryRow label="Language" value={state.language} />
          {state.videoType !== "remotion" ? <SummaryRow label="Avatar" value={avatarName} /> : null}
          {state.videoType !== "remotion" && state.voiceName ? <SummaryRow label="Voice" value={state.voiceName} /> : null}
          <SummaryRow label="Duration" value={duration} />
          {state.videoType === "remotion" ? (
            <SummaryRow
              label="Subtitles"
              value={state.includeCaptions ? `${state.subtitleColor} · ${state.subtitlePosition}` : "Disabled"}
            />
          ) : null}
          {state.videoType === "remotion" ? <SummaryRow label="Logo" value={state.logoFileName || "None"} /> : null}
          <SummaryRow label="Aspect Ratio" value={state.aspectRatio} />
          <SummaryRow label="Status" value={statusLabel} />
          {state.styledVideoUrl ? <SummaryRow label="Styled Output" value={state.subtitleSource} /> : null}
          {(generatedVideo?._id || generatedVideo?.video_id) ? <SummaryRow label="Video ID" value={generatedVideo._id || generatedVideo.video_id!} /> : null}
        </div>
      </div>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-start gap-3 text-sm">
      <span className="text-muted-foreground whitespace-nowrap shrink-0">{label}</span>
      <span className="text-foreground font-medium text-right break-all">{value}</span>
    </div>
  );
}

function getGenerationStatusLabel(
  status: WizardState["generationStatus"],
  isRemotion: boolean,
): string {
  if (status === "submitting") {
    return isRemotion ? "Rendering" : "Processing";
  }

  if (status === "styling") {
    return "Styling";
  }

  if (status === "completed") {
    return "Completed";
  }

  if (status === "failed") {
    return "Failed";
  }

  return "Idle";
}
