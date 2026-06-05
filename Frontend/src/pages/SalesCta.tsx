import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Loader2, Play, Pause, ExternalLink, RotateCcw } from "lucide-react";
import { fetchInteractiveSales, type InteractiveSales } from "@/lib/api";

export default function SalesCta() {
  const { id } = useParams<{ id: string }>();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasEnded, setHasEnded] = useState(false);

  const { data, isLoading, error } = useQuery<InteractiveSales>({
    queryKey: ["interactive-sales", id],
    queryFn: () => fetchInteractiveSales(id!),
    enabled: Boolean(id),
  });

  const shouldShowCta = Boolean(
    data?.sales_cta_label &&
    data?.sales_cta_url &&
    hasEnded
  );

  const openCta = () => {
    if (!data?.sales_cta_url) return;
    window.open(data.sales_cta_url, "_blank", "noopener,noreferrer");
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play().catch(console.error);
    }
  };

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handlePlay = () => {
      setIsPlaying(true);
      setHasEnded(false);
    };
    const handlePause = () => setIsPlaying(false);
    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      if (video.duration && video.currentTime >= video.duration - 0.5) {
        setHasEnded(true);
      }
    };
    const handleEnded = () => setHasEnded(true);

    video.addEventListener("play", handlePlay);
    video.addEventListener("pause", handlePause);
    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("ended", handleEnded);

    return () => {
      video.removeEventListener("play", handlePlay);
      video.removeEventListener("pause", handlePause);
      video.removeEventListener("timeupdate", handleTimeUpdate);
      video.removeEventListener("ended", handleEnded);
    };
  }, [data]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
        <div className="flex items-center gap-3 text-sm font-semibold">
          <Loader2 className="h-5 w-5 animate-spin text-emerald-500" />
          Loading video...
        </div>
      </div>
    );
  }

  if (error instanceof Error) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center px-6">
        <div className="max-w-md w-full rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-400" />
            <p className="text-sm font-semibold">Unable to load this video</p>
          </div>
          <p className="mt-3 text-sm text-white/70">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center px-6">
        <div className="max-w-md w-full rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <p className="text-sm font-semibold">Video not found</p>
          <p className="mt-3 text-sm text-white/70">This link may be invalid or the video is still processing.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white px-4 py-8 flex flex-col items-center justify-center">
      <div className="w-full max-w-[430px] flex flex-col gap-4">
        {/* Fullscreen Video Wrapper */}
        <div
          className="relative w-full overflow-hidden rounded-3xl bg-slate-900 shadow-2xl border border-white/10"
          style={{
            aspectRatio: "9 / 16",
            maxHeight: "min(82vh, 800px)",
          }}
        >
          <video
            ref={videoRef}
            src={data.video_url}
            playsInline
            controls
            className="w-full h-full object-cover"
          />

          {/* Top-Right Persistent CTA Button */}
          {Boolean(data.sales_cta_label && data.sales_cta_url) && (
            <button
              type="button"
              onClick={openCta}
              className="absolute pointer-events-auto rounded-full font-black text-white hover:scale-105 active:scale-95 flex items-center justify-center gap-1 z-20 transition-all duration-300 border border-white/10"
              style={{
                top: "2.8125%",
                right: "5%",
                height: "2.8125%",
                minHeight: "24px",
                maxHeight: "36px",
                background: "rgba(15, 191, 93, 0.95)",
                boxShadow: "0 8px 20px rgba(15, 191, 93, 0.35)",
                fontSize: "10.5px",
                padding: "0 12px",
                display: "flex",
                alignItems: "center",
              }}
            >
              <span>{data.sales_cta_label}</span>
              <ExternalLink className="h-3 w-3" />
            </button>
          )}

          {/* Top-Left Persistent Restart Button */}
          <button
            type="button"
            onClick={() => {
              const video = videoRef.current;
              if (!video) return;
              video.currentTime = 0;
              video.play().catch(console.error);
              setHasEnded(false);
            }}
            className="absolute pointer-events-auto rounded-full font-black text-white hover:scale-105 active:scale-95 flex items-center justify-center z-20 transition-all duration-300 border border-white/10"
            style={{
              top: "2.8125%",
              left: "5%",
              height: "2.8125%",
              width: "calc(54 / 1920 * 100vw)",
              minHeight: "24px",
              maxHeight: "36px",
              minWidth: "24px",
              maxWidth: "36px",
              background: "rgba(255, 255, 255, 0.18)",
              border: "1px solid rgba(255, 255, 255, 0.24)",
              boxShadow: "0 8px 20px rgba(0, 0, 0, 0.22)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            title="Restart Video"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>

          {/* Premium Bottom CTA Button Overlay (shows at the end of the video) */}
          {shouldShowCta && (
            <div
              className="absolute bottom-0 left-0 right-0 p-6 flex flex-col gap-3 pointer-events-none animate-fade-in z-20"
              style={{
                background: "linear-gradient(180deg, rgba(15, 23, 42, 0) 0%, rgba(15, 23, 42, 0.8) 35%, rgba(15, 23, 42, 0.95) 100%)",
              }}
            >
              <button
                type="button"
                onClick={openCta}
                className="pointer-events-auto w-full h-[54px] min-h-[54px] max-h-[54px] rounded-2xl font-extrabold text-[17px] text-white shadow-lg transition-all duration-300 transform active:scale-95 flex items-center justify-center gap-2 border border-white/20"
                style={{
                  background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                  boxShadow: "0 10px 25px rgba(16, 185, 129, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.3)",
                }}
              >
                <span>{data.sales_cta_label}</span>
                <ExternalLink className="h-4.5 w-4.5" />
              </button>
            </div>
          )}
        </div>

        <p className="text-center text-xs text-white/40 px-4">
          The video graphics are not interactive. Use the buttons on screen.
        </p>
      </div>
    </div>
  );
}
