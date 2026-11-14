import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { TemplateWorkspace } from "@/components/templates/TemplateWorkspace";
import { Button } from "@/components/ui/button";
import {
  listTemplates,
  TEMPLATE_LABELS,
  TEMPLATE_TYPES,
  type TemplateRecord,
  type TemplateType,
} from "@/lib/templates";

export function TemplatesPage() {
  const queryClient = useQueryClient();
  const templates = useQuery({
    queryKey: ["templates"],
    queryFn: listTemplates,
  });
  const [actor, setActor] = useState(() => window.localStorage.getItem("qaflow.actor") ?? "");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    window.localStorage.setItem("qaflow.actor", actor);
  }, [actor]);

  const records = templates.data ?? [];
  const selected =
    records.find((template) => template.id === selectedId) ??
    records.find((template) => template.is_active && template.type === "user_story") ??
    records[0];

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Templates</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            AI drafts and GrokBot results must match the active template. Saving an edit creates a
            new version and leaves the previous one unchanged.
          </p>
        </div>
        <label className="flex flex-col gap-1 text-sm" htmlFor="template-actor">
          Your name
          <input
            id="template-actor"
            className="rounded-md border border-input bg-background px-2 py-1 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={actor}
            autoComplete="name"
            onChange={(event) => setActor(event.target.value)}
          />
        </label>
      </div>

      {notice ? (
        <p role="status" className="text-sm">
          {notice}
        </p>
      ) : null}

      {templates.isPending ? <p role="status">Loading templates…</p> : null}
      {templates.isError ? (
        <p role="alert" className="text-sm text-destructive">
          Templates could not be loaded. {templates.error.message}
        </p>
      ) : null}

      {templates.isSuccess && records.length === 0 ? (
        <p className="text-sm">No templates are stored yet.</p>
      ) : null}

      {selected ? (
        <div className="grid items-start gap-6 lg:grid-cols-[16rem_minmax(0,1fr)]">
          <nav aria-label="Template versions" className="flex flex-col gap-4">
            {TEMPLATE_TYPES.map((type) => (
              <VersionGroup
                key={type}
                type={type}
                templates={records.filter((template) => template.type === type)}
                selectedId={selected.id}
                onSelect={setSelectedId}
              />
            ))}
            <Button type="button" variant="outline" onClick={() => void templates.refetch()}>
              Refresh
            </Button>
          </nav>
          <TemplateWorkspace
            key={selected.id}
            template={selected}
            actor={actor}
            onSaved={(saved, previousVersion) => {
              setSelectedId(saved.id);
              setNotice(
                `Saved ${TEMPLATE_LABELS[saved.type]} version ${saved.version}. Version ${previousVersion} was kept.`,
              );
              void queryClient.invalidateQueries({ queryKey: ["templates"] });
            }}
            onActivated={(saved) => {
              setSelectedId(saved.id);
              setNotice(
                `${TEMPLATE_LABELS[saved.type]} version ${saved.version} is now the active template.`,
              );
              void queryClient.invalidateQueries({ queryKey: ["templates"] });
            }}
          />
        </div>
      ) : null}
    </section>
  );
}

function VersionGroup({
  type,
  templates,
  selectedId,
  onSelect,
}: {
  type: TemplateType;
  templates: TemplateRecord[];
  selectedId: number;
  onSelect: (id: number) => void;
}) {
  const ordered = [...templates].sort((left, right) => right.version - left.version);
  return (
    <div className="flex flex-col gap-1">
      <h2 className="px-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {TEMPLATE_LABELS[type]}
      </h2>
      {ordered.length === 0 ? <p className="px-2 text-sm text-muted-foreground">None</p> : null}
      {ordered.map((template) => (
        <button
          key={template.id}
          type="button"
          aria-pressed={template.id === selectedId}
          className={[
            "rounded-md px-2 py-1.5 text-left text-sm",
            template.id === selectedId ? "bg-accent text-accent-foreground" : "hover:bg-muted",
          ].join(" ")}
          onClick={() => onSelect(template.id)}
        >
          Version {template.version}
          {template.is_active ? " · Active" : ""}
        </button>
      ))}
    </div>
  );
}
