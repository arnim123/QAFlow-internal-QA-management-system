import { useQuery } from "@tanstack/react-query";
import type { ColDef } from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";

import { Button } from "@/components/ui/button";
import { getHealth } from "@/lib/api";

const columnDefs: ColDef[] = [{ colId: "empty", headerName: "" }];
const rowData: unknown[] = [];

export function HomePage() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
  });

  const status = health.isPending
    ? "Checking API…"
    : health.isError
      ? "API unavailable"
      : `API status: ${health.data.status}`;

  return (
    <section className="flex max-w-3xl flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">QAFlow</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Internal QA management for Main Fast Trade Technologies.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={() => void health.refetch()}>
          Refresh
        </Button>
      </div>
      <p className="text-sm" role="status">
        {status}
      </p>
      <div className="h-64 w-full">
        <AgGridReact rowData={rowData} columnDefs={columnDefs} />
      </div>
    </section>
  );
}
