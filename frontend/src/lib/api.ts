export type HealthResponse = {
  status: string;
};

const base = import.meta.env.VITE_API_BASE_URL ?? "";

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${base}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed (${response.status})`);
  }
  return response.json() as Promise<HealthResponse>;
}
