import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  applyFields,
  columnsToRows,
  fieldDraftProblems,
  rowsToColumns,
  nextId,
  samplePayload,
  sampleValue,
  schemaToFields,
  type ColumnDraft,
  type FieldDraft,
  type JsonSchema,
} from "@/lib/schemaForm";
import {
  activateVersion,
  ApiError,
  createVersion,
  previewTemplate,
  TEMPLATE_LABELS,
  type FieldError,
  type TemplateRecord,
} from "@/lib/templates";

const inputClass =
  "w-full rounded-md border border-input bg-background px-2 py-1 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

const fieldTypes: FieldDraft["type"][] = [
  "string",
  "integer",
  "number",
  "boolean",
  "array",
  "object",
];

export function TemplateWorkspace({
  template,
  actor,
  onSaved,
  onActivated,
}: {
  template: TemplateRecord;
  actor: string;
  onSaved: (saved: TemplateRecord, previousVersion: number) => void;
  onActivated: (saved: TemplateRecord) => void;
}) {
  const [schemaText, setSchemaText] = useState(() => JSON.stringify(template.json_schema, null, 2));
  const [schemaObject, setSchemaObject] = useState<JsonSchema>(template.json_schema);
  const [fields, setFields] = useState<FieldDraft[] | null>(() => schemaToFields(template.json_schema));
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [columnRows, setColumnRows] = useState<ColumnDraft[]>(() => columnsToRows(template.columns) ?? []);
  const [columnsText, setColumnsText] = useState(() => JSON.stringify(template.columns, null, 2));
  const [columnsError, setColumnsError] = useState<string | null>(null);
  const [makeActive, setMakeActive] = useState(true);
  const [reason, setReason] = useState("");
  const [payloadText, setPayloadText] = useState(() =>
    JSON.stringify(samplePayload(template.json_schema), null, 2),
  );
  const [previewErrors, setPreviewErrors] = useState<FieldError[]>([]);
  const [previewOk, setPreviewOk] = useState(false);
  const [serverErrors, setServerErrors] = useState<FieldError[]>([]);
  const [serverMessage, setServerMessage] = useState<string | null>(null);
  const [pending, setPending] = useState<"save" | "activate" | "preview" | null>(null);

  const formProblem = fields ? fieldDraftProblems(fields) : null;
  const label = TEMPLATE_LABELS[template.type];
  let payloadValue: unknown;
  let payloadError: string | null = null;
  try {
    payloadValue = JSON.parse(payloadText) as unknown;
  } catch {
    payloadValue = null;
    payloadError = "Payload JSON is invalid.";
  }

  function onFields(next: FieldDraft[]) {
    setFields(next);
    const updated = applyFields(schemaObject, next);
    setSchemaObject(updated);
    setSchemaText(JSON.stringify(updated, null, 2));
    setSchemaError(fieldDraftProblems(next));
  }

  function onSchemaText(text: string) {
    setSchemaText(text);
    try {
      const parsed = JSON.parse(text) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        setSchemaError("Schema JSON must be an object.");
        return;
      }
      const schema = parsed as JsonSchema;
      setSchemaObject(schema);
      setFields(schemaToFields(schema));
      setSchemaError(null);
    } catch {
      setSchemaError("Schema JSON is invalid.");
    }
  }

  function onColumnRows(next: ColumnDraft[]) {
    setColumnRows(next);
    setColumnsText(JSON.stringify(rowsToColumns(next), null, 2));
    setColumnsError(null);
  }

  function onColumnsText(text: string) {
    setColumnsText(text);
    try {
      const parsed = JSON.parse(text) as unknown;
      const rows = columnsToRows(parsed);
      if (!rows) {
        setColumnsError("Columns JSON must be a list.");
        return;
      }
      setColumnRows(rows);
      setColumnsError(null);
    } catch {
      setColumnsError("Columns JSON is invalid.");
    }
  }

  async function save() {
    if (!actor.trim()) {
      setServerMessage("Enter your name so the audit log can record who changed the template.");
      return;
    }
    let parsedSchema: JsonSchema;
    let parsedColumns: ReturnType<typeof rowsToColumns>;
    try {
      parsedSchema = JSON.parse(schemaText) as JsonSchema;
      parsedColumns = JSON.parse(columnsText) as ReturnType<typeof rowsToColumns>;
    } catch {
      setServerMessage("Fix the JSON before saving.");
      return;
    }
    setPending("save");
    setServerErrors([]);
    setServerMessage(null);
    try {
      const saved = await createVersion(template.type, {
        json_schema: parsedSchema,
        columns: parsedColumns,
        activate: makeActive,
        actor: actor.trim(),
        reason: reason.trim() || undefined,
      });
      onSaved(saved, template.version);
    } catch (error) {
      showFailure(error, "The new version was not saved.");
    } finally {
      setPending(null);
    }
  }

  async function activate() {
    if (!actor.trim()) {
      setServerMessage("Enter your name so the audit log can record who activated the template.");
      return;
    }
    setPending("activate");
    setServerErrors([]);
    setServerMessage(null);
    try {
      const saved = await activateVersion(template.type, template.version, {
        actor: actor.trim(),
        reason: reason.trim() || undefined,
      });
      onActivated(saved);
    } catch (error) {
      showFailure(error, "The version was not activated.");
    } finally {
      setPending(null);
    }
  }

  async function preview() {
    if (payloadError || schemaError) {
      return;
    }
    setPending("preview");
    setPreviewErrors([]);
    setPreviewOk(false);
    try {
      await previewTemplate(template.type, {
        payload: payloadValue,
        json_schema: schemaObject,
      });
      setPreviewOk(true);
    } catch (error) {
      if (error instanceof ApiError) {
        setPreviewErrors(error.errors);
        if (error.errors.length === 0) {
          setServerMessage(error.message);
        }
      } else {
        setServerMessage("The preview request failed.");
      }
    } finally {
      setPending(null);
    }
  }

  function showFailure(error: unknown, fallback: string) {
    if (error instanceof ApiError) {
      setServerMessage(error.message);
      setServerErrors(error.errors);
      return;
    }
    setServerMessage(fallback);
  }

  const saveBlocked = Boolean(schemaError || columnsError || formProblem || pending);

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">
          {label} version {template.version}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {template.is_active
            ? "This is the active version. The executor and the AI generator use it."
            : "This version is kept for history. Activating it does not change its schema."}
        </p>
        {typeof schemaObject.description === "string" ? (
          <p className="mt-2 text-sm">{schemaObject.description}</p>
        ) : null}
      </div>

      {serverMessage ? (
        <p role="alert" className="text-sm text-destructive">
          {serverMessage}
        </p>
      ) : null}
      {serverErrors.length > 0 ? (
        <ul role="alert" className="flex flex-col gap-1 text-sm">
          {serverErrors.map((error) => (
            <li key={`${error.field}:${error.message}`}>
              <code className="font-medium">{error.field}</code> {error.message}
            </li>
          ))}
        </ul>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <section className="flex flex-col gap-3">
          <h3 className="text-sm font-semibold">Schema form</h3>
          {fields ? (
            <FieldList fields={fields} onChange={onFields} />
          ) : (
            <p className="text-sm text-muted-foreground">
              This schema uses features the form does not edit. Change the JSON instead.
            </p>
          )}
          {formProblem ? <p className="text-sm text-destructive">{formProblem}</p> : null}
        </section>
        <section className="flex flex-col gap-2">
          <label className="text-sm font-semibold" htmlFor="template-schema">
            Schema JSON
          </label>
          <textarea
            id="template-schema"
            className={`${inputClass} min-h-80 font-mono text-xs`}
            spellCheck={false}
            value={schemaText}
            onChange={(event) => onSchemaText(event.target.value)}
          />
          {schemaError ? (
            <p role="alert" className="text-sm text-destructive">
              {schemaError}
            </p>
          ) : null}
        </section>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <section className="flex flex-col gap-3">
          <h3 className="text-sm font-semibold">Display columns</h3>
          <ColumnEditor rows={columnRows} onChange={onColumnRows} />
        </section>
        <section className="flex flex-col gap-2">
          <label className="text-sm font-semibold" htmlFor="template-columns">
            Columns JSON
          </label>
          <textarea
            id="template-columns"
            className={`${inputClass} min-h-48 font-mono text-xs`}
            spellCheck={false}
            value={columnsText}
            onChange={(event) => onColumnsText(event.target.value)}
          />
          {columnsError ? (
            <p role="alert" className="text-sm text-destructive">
              {columnsError}
            </p>
          ) : null}
        </section>
      </div>

      <section className="flex flex-col gap-3 rounded-lg border border-border p-4">
        <h3 className="text-sm font-semibold">Preview</h3>
        <ColumnPreview rows={columnRows} />
        <div className="grid gap-4 xl:grid-cols-2">
          <div>
            {payloadError ? (
              <p className="text-sm text-destructive">{payloadError}</p>
            ) : (
              <PreviewFields
                schema={schemaObject}
                value={payloadValue}
                columns={columnRows}
                onChange={(next) => {
                  setPayloadText(JSON.stringify(next, null, 2));
                  setPreviewOk(false);
                  setPreviewErrors([]);
                }}
              />
            )}
          </div>
          <label className="flex flex-col gap-2 text-sm" htmlFor="template-payload">
            <span className="font-medium">Sample payload</span>
            <textarea
              id="template-payload"
              className={`${inputClass} min-h-64 font-mono text-xs`}
              spellCheck={false}
              value={payloadText}
              onChange={(event) => {
                setPayloadText(event.target.value);
                setPreviewOk(false);
                setPreviewErrors([]);
              }}
            />
          </label>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" disabled={pending !== null} onClick={() => void preview()}>
            {pending === "preview" ? "Checking…" : "Check payload"}
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setPayloadText(JSON.stringify(samplePayload(schemaObject), null, 2));
              setPreviewOk(false);
              setPreviewErrors([]);
            }}
          >
            Reset sample
          </Button>
        </div>
        {previewOk ? (
          <p role="status" className="text-sm">
            Payload matches this schema.
          </p>
        ) : null}
        {previewErrors.length > 0 ? (
          <ul role="alert" className="flex flex-col gap-1 text-sm">
            {previewErrors.map((error) => (
              <li key={`${error.field}:${error.message}`}>
                <code className="font-medium">{error.field}</code> {error.message}
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <form
        className="flex flex-col gap-3 border-t border-border pt-4"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <p className="text-sm text-muted-foreground">
          Saving creates version {template.version + 1}. Version {template.version} stays as it is.
        </p>
        <label className="flex flex-col gap-1 text-sm" htmlFor="template-reason">
          Reason
          <input
            id="template-reason"
            className={inputClass}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={makeActive}
            onChange={(event) => setMakeActive(event.target.checked)}
          />
          Make this the active version
        </label>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={saveBlocked}>
            {pending === "save" ? "Saving…" : "Save as new version"}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={template.is_active || pending !== null}
            onClick={() => void activate()}
          >
            {pending === "activate" ? "Activating…" : `Activate stored version ${template.version}`}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          Activate uses the stored version, not unsaved edits.
        </p>
      </form>
    </div>
  );
}

function FieldList({
  fields,
  onChange,
}: {
  fields: FieldDraft[];
  onChange: (next: FieldDraft[]) => void;
}) {
  function update(index: number, next: FieldDraft) {
    onChange(fields.map((field, fieldIndex) => (fieldIndex === index ? next : field)));
  }

  return (
    <div className="flex flex-col gap-3">
      {fields.map((field, index) => (
        <fieldset key={field.id} className="flex flex-col gap-2 rounded-md border border-border p-3">
          <legend className="px-1 text-xs text-muted-foreground">Property</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              Name
              <input
                className={inputClass}
                value={field.name}
                onChange={(event) => update(index, { ...field, name: event.target.value })}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Type
              <select
                className={inputClass}
                value={field.type}
                onChange={(event) =>
                  update(index, { ...field, type: event.target.value as FieldDraft["type"] })
                }
              >
                {fieldTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={field.required}
              onChange={(event) => update(index, { ...field, required: event.target.checked })}
            />
            Required
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Description
            <input
              className={inputClass}
              value={field.description}
              onChange={(event) => update(index, { ...field, description: event.target.value })}
            />
          </label>
          {field.type === "string" ? (
            <label className="flex flex-col gap-1 text-sm">
              Allowed values, comma separated
              <input
                className={inputClass}
                value={field.enumText}
                onChange={(event) => update(index, { ...field, enumText: event.target.value })}
              />
            </label>
          ) : null}
          {field.type === "array" ? (
            <label className="flex flex-col gap-1 text-sm">
              Item type
              <select
                className={inputClass}
                value={field.itemType}
                onChange={(event) =>
                  update(index, {
                    ...field,
                    itemType: event.target.value as FieldDraft["itemType"],
                    children: event.target.value === "object" ? field.children : [],
                  })
                }
              >
                <option value="string">string</option>
                <option value="object">object</option>
              </select>
            </label>
          ) : null}
          {field.type === "object" || (field.type === "array" && field.itemType === "object") ? (
            <div className="ml-3 border-l border-border pl-3">
              <p className="mb-2 text-xs text-muted-foreground">Nested properties</p>
              <FieldList
                fields={field.children}
                onChange={(children) => update(index, { ...field, children })}
              />
            </div>
          ) : null}
          <Button
            type="button"
            variant="ghost"
            onClick={() => onChange(fields.filter((item) => item.id !== field.id))}
          >
            Remove property
          </Button>
        </fieldset>
      ))}
      <Button
        type="button"
        variant="outline"
        onClick={() =>
          onChange([
            ...fields,
            {
              id: nextId(),
              name: "",
              type: "string",
              required: false,
              description: "",
              enumText: "",
              itemType: "string",
              children: [],
            },
          ])
        }
      >
        Add property
      </Button>
    </div>
  );
}

function ColumnEditor({
  rows,
  onChange,
}: {
  rows: ColumnDraft[];
  onChange: (next: ColumnDraft[]) => void;
}) {
  function update(index: number, patch: Partial<ColumnDraft>) {
    onChange(rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  return (
    <div className="flex flex-col gap-2">
      {rows.map((row, index) => (
        <div key={row.id} className="grid gap-2 sm:grid-cols-[1fr_1fr_1fr_auto]">
          <input
            aria-label={`Column ${index + 1} key`}
            className={inputClass}
            value={row.key}
            placeholder="key"
            onChange={(event) => update(index, { key: event.target.value })}
          />
          <input
            aria-label={`Column ${index + 1} label`}
            className={inputClass}
            value={row.label}
            placeholder="label"
            onChange={(event) => update(index, { label: event.target.value })}
          />
          <input
            aria-label={`Column ${index + 1} section`}
            className={inputClass}
            value={row.section}
            placeholder="section"
            onChange={(event) => update(index, { section: event.target.value })}
          />
          <Button
            type="button"
            variant="ghost"
            onClick={() => onChange(rows.filter((item) => item.id !== row.id))}
          >
            Remove
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="outline"
        onClick={() =>
          onChange([...rows, { id: nextId(), key: "", label: "", section: "" }])
        }
      >
        Add column
      </Button>
    </div>
  );
}

function ColumnPreview({ rows }: { rows: ColumnDraft[] }) {
  const showSections = rows.some((row) => row.section.trim());
  const groups: { section: string; columns: ColumnDraft[] }[] = [];
  for (const row of rows) {
    const section = row.section.trim() || "Columns";
    const last = groups.at(-1);
    if (!last || last.section !== section) {
      groups.push({ section, columns: [row] });
    } else {
      last.columns.push(row);
    }
  }

  return (
    <div className="flex flex-col gap-3 overflow-x-auto">
      {groups.map((group) => (
        <div key={group.section}>
          {showSections ? <p className="mb-1 text-xs font-medium">{group.section}</p> : null}
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr>
                {group.columns.map((column) => (
                  <th key={column.id} className="border border-border px-2 py-1 font-medium">
                    {column.label || column.key}
                  </th>
                ))}
              </tr>
            </thead>
          </table>
        </div>
      ))}
    </div>
  );
}

function PreviewFields({
  schema,
  value,
  columns,
  onChange,
}: {
  schema: JsonSchema;
  value: unknown;
  columns: ColumnDraft[];
  onChange: (next: unknown) => void;
}) {
  if (schema.type === "object" && schema.properties) {
    const record = isRecord(value) ? value : {};
    return (
      <div className="flex flex-col gap-3">
        {Object.entries(schema.properties).map(([key, property]) => (
          <div key={key} className="flex flex-col gap-1">
            <span className="text-sm font-medium">{columnLabel(key, columns)}</span>
            {property.description ? (
              <span className="text-xs text-muted-foreground">{property.description}</span>
            ) : null}
            <PreviewFields
              schema={property}
              value={record[key]}
              columns={columns}
              onChange={(next) => onChange({ ...record, [key]: next })}
            />
          </div>
        ))}
      </div>
    );
  }

  if (schema.type === "array") {
    const items = Array.isArray(value) ? value : [];
    const itemSchema = schema.items ?? { type: "string" };
    return (
      <div className="flex flex-col gap-2">
        {items.map((item, index) => (
          <div key={index} className="rounded-md border border-border p-2">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs text-muted-foreground">Item {index + 1}</span>
              <Button
                type="button"
                variant="ghost"
                onClick={() => onChange(items.filter((_, itemIndex) => itemIndex !== index))}
              >
                Remove
              </Button>
            </div>
            <PreviewFields
              schema={itemSchema}
              value={item}
              columns={columns}
              onChange={(next) => {
                const copy = [...items];
                copy[index] = next;
                onChange(copy);
              }}
            />
          </div>
        ))}
        <Button type="button" variant="outline" onClick={() => onChange([...items, sampleValue(itemSchema)])}>
          Add item
        </Button>
      </div>
    );
  }

  if (schema.enum && schema.enum.length > 0) {
    const current = typeof value === "string" ? value : schema.enum[0];
    return (
      <select className={inputClass} value={current} onChange={(event) => onChange(event.target.value)}>
        {schema.enum.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }

  if (schema.type === "integer" || schema.type === "number") {
    return (
      <input
        className={inputClass}
        type="number"
        value={typeof value === "number" ? value : ""}
        onChange={(event) => onChange(event.target.value === "" ? "" : Number(event.target.value))}
      />
    );
  }

  return (
    <input
      className={inputClass}
      type="text"
      value={typeof value === "string" ? value : ""}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

function columnLabel(key: string, columns: ColumnDraft[]): string {
  return columns.find((column) => column.key === key)?.label ?? key;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
