import type { JsonSchema } from "@/lib/schemaForm";

export type TemplateType =
  | "user_story"
  | "requirement"
  | "test_case"
  | "execution_result"
  | "report";

export type TemplateColumn = {
  key: string;
  label: string;
  section: string | null;
};

export type TemplateRecord = {
  id: number;
  type: TemplateType;
  version: number;
  is_active: boolean;
  json_schema: JsonSchema;
  columns: TemplateColumn[];
  created_at: string;
  updated_at: string;
};

export type FieldError = {
  field: string;
  message: string;
};

export class ApiError extends Error {
  status: number;
  errors: FieldError[];

  constructor(status: number, detail: string, errors: FieldError[]) {
    super(detail);
    this.status = status;
    this.errors = errors;
  }
}

const base = import.meta.env.VITE_API_BASE_URL ?? "";

export const TEMPLATE_TYPES: TemplateType[] = [
  "user_story",
  "requirement",
  "test_case",
  "execution_result",
  "report",
];

export const TEMPLATE_LABELS: Record<TemplateType, string> = {
  user_story: "User story",
  requirement: "Requirement",
  test_case: "Test case",
  execution_result: "Execution result",
  report: "Report",
};

export function listTemplates(): Promise<TemplateRecord[]> {
  return request<TemplateRecord[]>("/api/templates");
}

export function createVersion(
  type: TemplateType,
  body: {
    json_schema: JsonSchema;
    columns: TemplateColumn[];
    activate: boolean;
    actor: string;
    reason?: string;
  },
): Promise<TemplateRecord> {
  return request<TemplateRecord>(`/api/templates/${type}/versions`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function activateVersion(
  type: TemplateType,
  version: number,
  body: { actor: string; reason?: string },
): Promise<TemplateRecord> {
  return request<TemplateRecord>(`/api/templates/${type}/versions/${version}/activate`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function previewTemplate(
  type: TemplateType,
  body: { payload: unknown; json_schema?: JsonSchema },
): Promise<{ valid: boolean; errors: FieldError[] }> {
  return request(`/api/templates/${type}/preview`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    throw await readError(response);
  }
  return response.json() as Promise<T>;
}

async function readError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as {
      detail?: unknown;
      errors?: FieldError[];
    };
    if (Array.isArray(body.errors) && body.errors.length > 0) {
      const detail = typeof body.detail === "string" ? body.detail : "The template rejected this";
      return new ApiError(response.status, detail, body.errors);
    }
    if (Array.isArray(body.detail)) {
      const errors = body.detail.map((item) => {
        const record = item as { loc?: unknown[]; msg?: string };
        const field = Array.isArray(record.loc) ? record.loc.map(String).join(".") : "(request)";
        return { field, message: record.msg ?? "Invalid" };
      });
      return new ApiError(response.status, "The request is invalid", errors);
    }
    const detail = typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`;
    return new ApiError(response.status, detail, []);
  } catch {
    return new ApiError(response.status, `Request failed (${response.status})`, []);
  }
}
