"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useSession } from "@/lib/auth-client";
import { ArrowLeft, Download, Clock, Star, AlertCircle, Trash2, Edit2, X, Check } from "lucide-react";
import Link from "next/link";
import DynamicVideoPlayer from "@/components/dynamic-video-player";

interface Clip {
  id: string;
  filename: string;
  file_path: string;
  start_time: string;
  end_time: string;
  duration: number;
  text: string;
  relevance_score: number;
  reasoning: string;
  clip_order: number;
  created_at: string;
  video_url: string;
}

interface TaskDetails {
  id: string;
  user_id: string;
  source_id: string;
  source_title: string;
  source_type: string;
  status: string;
  progress?: number;
  progress_message?: string;
  clips_count: number;
  created_at: string;
  updated_at: string;
  font_family?: string;
  font_size?: number;
  font_color?: string;
}

export default function TaskPage() {
  const params = useParams();
  const router = useRouter();
  const { data: session } = useSession();
  const [task, setTask] = useState<TaskDetails | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState("");
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deletingClipId, setDeletingClipId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchTaskStatus = async (retryCount = 0, maxRetries = 5) => {
    if (!params.id) return false;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      // Fetch task details (including status)
      // Don't wait for session - fetch immediately with user_id if available
      const headers: HeadersInit = {};
      if (session?.user?.id) {
        headers["user_id"] = session.user.id;
      }

      const taskResponse = await fetch(`${apiUrl}/tasks/${params.id}`, {
        headers,
      });

      // Handle 404 with retry logic (task might not be persisted yet)
      if (taskResponse.status === 404 && retryCount < maxRetries) {
        console.log(`Task not found yet, retrying in ${(retryCount + 1) * 500}ms... (${retryCount + 1}/${maxRetries})`);
        await new Promise((resolve) => setTimeout(resolve, (retryCount + 1) * 500));
        return fetchTaskStatus(retryCount + 1, maxRetries);
      }

      if (!taskResponse.ok) {
        throw new Error(`Failed to fetch task: ${taskResponse.status}`);
      }

      const taskData = await taskResponse.json();
      setTask(taskData);

      // Use clips from the main task response
      if (taskData.status === "completed" && taskData.clips) {
        setClips(taskData.clips);
      }

      return true;
    } catch (err) {
      console.error("Error fetching task data:", err);
      setError(err instanceof Error ? err.message : "Failed to load task");
      return false;
    }
  };

  // Initial fetch - runs immediately, doesn't wait for session
  useEffect(() => {
    if (!params.id) return;

    const fetchTaskData = async () => {
      try {
        setIsLoading(true);
        await fetchTaskStatus();
      } finally {
        setIsLoading(false);
      }
    };

    fetchTaskData();
  }, [params.id]); // Only run once when params change

  // SSE effect - real-time progress updates
  useEffect(() => {
    if (!params.id || !task) return;

    // Only connect to SSE if task is queued or processing
    if (task.status !== "queued" && task.status !== "processing") return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const eventSource = new EventSource(`${apiUrl}/tasks/${params.id}/progress`);

    console.log("📡 Connected to SSE for real-time progress");

    eventSource.addEventListener("status", (e) => {
      const data = JSON.parse(e.data);
      console.log("📊 Status:", data);
      setProgress(data.progress || 0);
      setProgressMessage(data.message || "");
    });

    eventSource.addEventListener("progress", async (e) => {
      const data = JSON.parse(e.data);
      console.log("📈 Progress:", data);
      setProgress(data.progress || 0);
      setProgressMessage(data.message || "");

      // Update task status if provided
      if (data.status && task) {
        setTask({ ...task, status: data.status });

        // If task just completed, fetch clips
        if (data.status === "completed") {
          console.log("🎬 Task completed, fetching clips...");
          await fetchTaskStatus();
        }
      }

      // Also fetch clips when progress reaches 100%
      if (data.progress === 100 && task?.status !== "completed") {
        console.log("💯 Progress 100%, fetching final status...");
        await fetchTaskStatus();
      }
    });

    eventSource.addEventListener("close", async (e) => {
      const data = JSON.parse(e.data);
      console.log("✅ Task completed:", data.status);
      eventSource.close();

      // Refresh task and clips (without showing loading skeleton)
      await fetchTaskStatus();
    });

    eventSource.addEventListener("error", (e) => {
      console.error("❌ SSE error:", e);
      if (e.data) {
        const data = JSON.parse(e.data);
        setError(data.error || "Connection error");
      }
      eventSource.close();
    });

    return () => {
      console.log("🔌 Disconnecting SSE");
      eventSource.close();
    };
  }, [params.id, task?.status]); // Re-run when task status changes

  // Polling fallback: if task is completed but no clips, keep checking
  useEffect(() => {
    if (!task || task.status !== "completed" || clips.length > 0) return;

    console.log("⏰ Task completed but no clips yet, polling...");

    const pollInterval = setInterval(async () => {
      console.log("🔄 Polling for clips...");
      const success = await fetchTaskStatus();

      // Stop polling if we got clips or if fetch failed
      if (!success || clips.length > 0) {
        clearInterval(pollInterval);
      }
    }, 2000); // Poll every 2 seconds

    // Stop polling after 30 seconds
    const timeout = setTimeout(() => {
      console.log("⏱️ Polling timeout reached");
      clearInterval(pollInterval);
    }, 30000);

    return () => {
      clearInterval(pollInterval);
      clearTimeout(timeout);
    };
  }, [task?.status, clips.length]); // Re-run when status or clips change

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "bg-green-100 text-green-800";
    if (score >= 0.6) return "bg-yellow-100 text-yellow-800";
    return "bg-red-100 text-red-800";
  };

  const handleEditTitle = async () => {
    if (!editedTitle.trim() || !session?.user?.id || !params.id) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/tasks/${params.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          user_id: session.user.id,
        },
        body: JSON.stringify({ title: editedTitle }),
      });

      if (response.ok) {
        setTask(task ? { ...task, source_title: editedTitle } : null);
        setIsEditing(false);
      } else {
        alert("Failed to update title");
      }
    } catch (err) {
      console.error("Error updating title:", err);
      alert("Failed to update title");
    }
  };

  const handleDeleteTask = async () => {
    if (!session?.user?.id || !params.id) return;

    setIsDeleting(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/tasks/${params.id}`, {
        method: "DELETE",
        headers: {
          user_id: session.user.id,
        },
      });

      if (response.ok) {
        router.push("/list");
      } else {
        alert("Failed to delete task");
      }
    } catch (err) {
      console.error("Error deleting task:", err);
      alert("Failed to delete task");
    } finally {
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  const handleDeleteClip = async (clipId: string) => {
    if (!session?.user?.id || !params.id) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/tasks/${params.id}/clips/${clipId}`, {
        method: "DELETE",
        headers: {
          user_id: session.user.id,
        },
      });

      if (response.ok) {
        setClips(clips.filter((clip) => clip.id !== clipId));
        setDeletingClipId(null);
      } else {
        alert("Failed to delete clip");
      }
    } catch (err) {
      console.error("Error deleting clip:", err);
      alert("Failed to delete clip");
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white p-4">
        <div className="max-w-6xl mx-auto">
          <div className="mb-6">
            <Skeleton className="h-8 w-48 mb-2" />
            <Skeleton className="h-4 w-96" />
          </div>
          <div className="grid gap-6">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <Skeleton className="h-48 w-full mb-4" />
                  <Skeleton className="h-4 w-full mb-2" />
                  <Skeleton className="h-4 w-3/4" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white p-4">
        <div className="max-w-6xl mx-auto">
          <Alert>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <Link href="/" className="mt-4 inline-block">
            <Button variant="outline">
              <ArrowLeft className="w-4 h-4" />
              Back to Home
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center gap-4 mb-4">
            <Link href="/">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4" />
                Back
              </Button>
            </Link>
          </div>

          {task && (
            <div>
              <div className="flex items-center gap-3 mb-2">
                {isEditing ? (
                  <div className="flex items-center gap-2 flex-1">
                    <Input
                      value={editedTitle}
                      onChange={(e) => setEditedTitle(e.target.value)}
                      className="text-2xl font-bold h-auto py-1"
                      autoFocus
                    />
                    <Button size="sm" onClick={handleEditTitle} disabled={!editedTitle.trim()}>
                      <Check className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setIsEditing(false);
                        setEditedTitle(task.source_title);
                      }}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ) : (
                  <>
                    <h1 className="text-2xl font-bold text-black">{task.source_title}</h1>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setIsEditing(true);
                        setEditedTitle(task.source_title);
                      }}
                    >
                      <Edit2 className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      onClick={() => setShowDeleteDialog(true)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </>
                )}
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <Badge variant="outline" className="capitalize">
                  {task.source_type}
                </Badge>
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {new Date(task.created_at).toLocaleDateString()}
                </span>
                {task.status === "completed" ? (
                  <span>
                    {clips.length} {clips.length === 1 ? "clip" : "clips"} generated
                  </span>
                ) : task.status === "processing" ? (
                  <Badge className="bg-blue-100 text-blue-800">Processing</Badge>
                ) : task.status === "queued" ? (
                  <Badge className="bg-yellow-100 text-yellow-800">Queued</Badge>
                ) : (
                  <Badge variant="outline" className="capitalize">
                    {task.status}
                  </Badge>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {task?.status === "processing" || task?.status === "queued" || !task ? (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-xl font-semibold text-black mb-2">
                {!task ? "Initializing..." : task.status === "queued" ? "Queued for Processing" : "Processing Video"}
              </h2>
              <p className="text-gray-600">
                {!task
                  ? "Setting up your task. This should only take a moment..."
                  : task.status === "queued"
                    ? "Your task is in the queue and will start processing shortly."
                    : "Generating clips from your video. This usually takes 2-3 minutes."}
              </p>
            </div>

            {/* Processing Status Display with Progress */}
            <Card className="mb-6">
              <CardContent className="p-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-center gap-3">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                    <p className="text-sm font-medium text-black">
                      {progressMessage ||
                        (!task ? "Initializing your task..." : "Processing video and generating clips...")}
                    </p>
                  </div>

                  {/* Progress Bar */}
                  {progress > 0 && (
                    <div className="w-full">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-gray-500">Progress</span>
                        <span className="text-xs font-medium text-blue-600">{progress}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  <p className="text-xs text-gray-500 text-center">
                    This page will automatically update when your clips are ready
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Skeleton for clips being generated */}
            {[1, 2].map((i) => (
              <Card key={i} className="overflow-hidden">
                <CardContent className="p-0">
                  <div className="flex flex-col lg:flex-row">
                    {/* Video Player Skeleton */}
                    <div className="bg-gray-200 relative flex-shrink-0 flex items-center justify-center w-full lg:w-96 h-48 lg:h-64">
                      <Skeleton className="w-full h-full" />
                    </div>

                    {/* Clip Details Skeleton */}
                    <div className="p-6 flex-1">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <Skeleton className="h-6 w-24 mb-2" />
                          <Skeleton className="h-4 w-32" />
                        </div>
                        <Skeleton className="h-6 w-12" />
                      </div>

                      <div className="mb-4">
                        <Skeleton className="h-4 w-16 mb-2" />
                        <Skeleton className="h-20 w-full" />
                      </div>

                      <div className="mb-4">
                        <Skeleton className="h-4 w-20 mb-2" />
                        <Skeleton className="h-4 w-full mb-1" />
                        <Skeleton className="h-4 w-3/4" />
                      </div>

                      <Skeleton className="h-8 w-24" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : task?.status === "error" ? (
          <Card>
            <CardContent className="p-8 text-center">
              <div className="text-red-600 mb-4">
                <AlertCircle className="w-12 h-12 mx-auto mb-2" />
                <h2 className="text-xl font-semibold">Processing Failed</h2>
              </div>
              <p className="text-gray-600 mb-4">There was an error processing your video. Please try again.</p>
              <Link href="/">
                <Button>
                  <ArrowLeft className="w-4 h-4" />
                  Back to Home
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : clips.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center">
              {task?.status === "completed" ? (
                <>
                  <div className="text-yellow-600 mb-4">
                    <AlertCircle className="w-12 h-12 mx-auto mb-2" />
                    <h2 className="text-xl font-semibold">Loading Clips...</h2>
                  </div>
                  <p className="text-gray-600 mb-4">
                    Your clips are ready! They should appear automatically in a moment.
                  </p>
                  <div className="flex gap-2 justify-center">
                    <Button
                      onClick={async () => {
                        console.log("🔄 Manual refresh triggered");
                        await fetchTaskStatus();
                      }}
                    >
                      Load Clips Now
                    </Button>
                    <Link href="/">
                      <Button variant="outline">
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Back to Home
                      </Button>
                    </Link>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Clock className="w-8 h-8 text-blue-500 animate-pulse" />
                  </div>
                  <h2 className="text-xl font-semibold text-black mb-2">Still Generating...</h2>
                  <p className="text-gray-600">
                    Your clips are being generated. This page will refresh automatically when they're ready.
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6">
            {/* Font Settings Display */}
            {task && (
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-sm font-medium text-black mb-3 flex items-center gap-2">
                  <span className="w-4 h-4">🎨</span>
                  Font Settings
                </h3>
                <div className="grid grid-cols-3 gap-4 text-xs">
                  <div>
                    <span className="text-gray-500">Font:</span>
                    <p className="font-medium">{task.font_family || "Default"}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Size:</span>
                    <p className="font-medium">{task.font_size || 24}px</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Color:</span>
                    <div className="flex items-center gap-1">
                      <div
                        className="w-3 h-3 rounded border"
                        style={{ backgroundColor: task.font_color || "#FFFFFF" }}
                      ></div>
                      <p className="font-medium">{task.font_color || "#FFFFFF"}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
            {clips.map((clip) => (
              <Card key={clip.id} className="overflow-hidden">
                <CardContent className="p-0">
                  <div className="flex flex-col lg:flex-row">
                    {/* Video Player */}
                    <div className="bg-black relative flex-shrink-0 flex items-center justify-center">
                      <DynamicVideoPlayer
                        src={`http://localhost:8000${clip.video_url}`}
                        poster="/placeholder-video.jpg"
                      />
                    </div>

                    {/* Clip Details */}
                    <div className="p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="font-semibold text-lg text-black mb-1">Clip {clip.clip_order}</h3>
                          <div className="flex items-center gap-2 text-sm text-gray-600">
                            <span>
                              {clip.start_time} - {clip.end_time}
                            </span>
                            <span>•</span>
                            <span>{formatDuration(clip.duration)}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className={getScoreColor(clip.relevance_score)}>
                            <Star className="w-3 h-3 mr-1" />
                            {(clip.relevance_score * 100).toFixed(0)}%
                          </Badge>
                        </div>
                      </div>

                      {clip.text && (
                        <div className="mb-4">
                          <h4 className="font-medium text-black mb-2">Transcript</h4>
                          <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded">{clip.text}</p>
                        </div>
                      )}

                      {clip.reasoning && (
                        <div className="mb-4">
                          <h4 className="font-medium text-black mb-2">AI Analysis</h4>
                          <p className="text-sm text-gray-600">{clip.reasoning}</p>
                        </div>
                      )}

                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" asChild>
                          <a href={`http://localhost:8000${clip.video_url}`} download={clip.filename}>
                            <Download className="w-4 h-4 mr-2" />
                            Download
                          </a>
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200"
                          onClick={() => setDeletingClipId(clip.id)}
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Delete Task Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Generation</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this generation? This will permanently delete all clips and cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteTask} disabled={isDeleting} className="bg-red-600 hover:bg-red-700">
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Clip Confirmation Dialog */}
      <AlertDialog open={!!deletingClipId} onOpenChange={(open) => !open && setDeletingClipId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Clip</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this clip? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingClipId && handleDeleteClip(deletingClipId)}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
