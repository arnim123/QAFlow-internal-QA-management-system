export type JsonSchema = {
  type?: string;
  description?: string;
  properties?: Record<string, JsonSchema>;
  required?: string[];
  items?: JsonSchema;
  enum?: string[];
  additionalProperties?: boolean;
  minLength?: number;
  minItems?: number;
  minimum?: number;
  $schema?: string;
  [key: string]: unknown;
};

export type FieldDraft = {
  id: string;
  name: string;
  type: "string" | "integer" | "number" | "boolean" | "array" | "object";
  required: boolean;
  description: string;
  enumText: string;
  itemType: "string" | "object";
  children: FieldDraft[];
};

export type ColumnDraft = {
  id: string;
  key: string;
  label: string;
  section: string;
};

const fieldTypes = ["string", "integer", "number", "boolean", "array", "object"] as const;

let sequence = 0;

export function nextId(): string {
  sequence += 1;
  return `field-${sequence}`;
}

export function schemaToFields(schema: JsonSchema): FieldDraft[] | null {
  if (schema.type !== "object" || !schema.properties) {
    return schema.type === "object" ? [] : null;
  }
  const required = new Set(schema.required ?? []);
  const fields: FieldDraft[] = [];
  for (const [name, property] of Object.entries(schema.properties)) {
    const field = propertyToField(name, property, required.has(name));
    if (!field) {
      return null;
    }
    fields.push(field);
  }
  return fields;
}

export function applyFields(root: JsonSchema, fields: FieldDraft[]): JsonSchema {
  const rest: JsonSchema = { ...root };
  delete rest.properties;
  delete rest.required;
  const properties: Record<string, JsonSchema> = {};
  const required: string[] = [];
  for (const field of fields) {
    const name = field.name.trim();
    if (!name) {
      continue;
    }
    properties[name] = fieldToProperty(field, root.properties?.[name]);
    if (field.required) {
      required.push(name);
    }
  }
  return { ...rest, type: "object", properties, required };
}

export function fieldDraftProblems(fields: FieldDraft[]): string | null {
  const names = fields.map((field) => field.name.trim()).filter(Boolean);
  const seen = new Set<string>();
  for (const name of names) {
    if (seen.has(name)) {
      return `Duplicate property "${name}"`;
    }
    seen.add(name);
  }
  if (fields.some((field) => !field.name.trim())) {
    return "Name every property before saving.";
  }
  for (const field of fields) {
    if (field.type === "object" || (field.type === "array" && field.itemType === "object")) {
      const nested = fieldDraftProblems(field.children);
      if (nested) {
        return nested;
      }
    }
  }
  return null;
}

export function samplePayload(schema: JsonSchema): unknown {
  return sampleValue(schema);
}

export function rowsToColumns(rows: ColumnDraft[]): { key: string; label: string; section: string | null }[] {
  return rows.map((row) => ({
    key: row.key.trim(),
    label: row.label.trim(),
    section: row.section.trim() || null,
  }));
}

export function columnsToRows(columns: unknown): ColumnDraft[] | null {
  if (!Array.isArray(columns)) {
    return null;
  }
  return columns.map((column) => {
    const record = column && typeof column === "object" ? (column as Record<string, unknown>) : {};
    return {
      id: nextId(),
      key: typeof record.key === "string" ? record.key : "",
      label: typeof record.label === "string" ? record.label : "",
      section: typeof record.section === "string" ? record.section : "",
    };
  });
}

function propertyToField(name: string, property: JsonSchema, required: boolean): FieldDraft | null {
  if (!property || typeof property !== "object" || !isFieldType(property.type)) {
    return null;
  }
  const field: FieldDraft = {
    id: nextId(),
    name,
    type: property.type,
    required,
    description: typeof property.description === "string" ? property.description : "",
    enumText: Array.isArray(property.enum) ? property.enum.join(", ") : "",
    itemType: "string",
    children: [],
  };
  if (property.type === "object") {
    const children = schemaToFields(property);
    if (!children) {
      return null;
    }
    field.children = children;
  }
  if (property.type === "array") {
    const items = property.items;
    if (!items || items.type === "string" || items.type === undefined) {
      field.itemType = "string";
    } else if (items.type === "object") {
      field.itemType = "object";
      const children = schemaToFields(items);
      if (!children) {
        return null;
      }
      field.children = children;
    } else {
      return null;
    }
  }
  return field;
}

function fieldToProperty(field: FieldDraft, previous: JsonSchema | undefined): JsonSchema {
  const property: JsonSchema = {};
  if (field.description.trim()) {
    property.description = field.description.trim();
  }
  property.type = field.type;
  if (field.type === "string") {
    const enums = field.enumText
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    if (enums.length > 0) {
      property.enum = enums;
    }
    if (typeof previous?.minLength === "number") {
      property.minLength = previous.minLength;
    }
  }
  if ((field.type === "integer" || field.type === "number") && typeof previous?.minimum === "number") {
    property.minimum = previous.minimum;
  }
  if (field.type === "array") {
    if (typeof previous?.minItems === "number") {
      property.minItems = previous.minItems;
    }
    if (field.itemType === "object") {
      property.items = objectSchema(field.children, previous?.items);
    } else {
      property.items = { type: "string" };
      if (typeof previous?.items?.minLength === "number") {
        property.items.minLength = previous.items.minLength;
      }
    }
  }
  if (field.type === "object") {
    const nested = objectSchema(field.children, previous);
    property.properties = nested.properties;
    property.required = nested.required;
    property.additionalProperties = nested.additionalProperties;
  }
  return property;
}

function objectSchema(fields: FieldDraft[], previous: JsonSchema | undefined): JsonSchema {
  const properties: Record<string, JsonSchema> = {};
  const required: string[] = [];
  for (const field of fields) {
    const name = field.name.trim();
    if (!name) {
      continue;
    }
    properties[name] = fieldToProperty(field, previous?.properties?.[name]);
    if (field.required) {
      required.push(name);
    }
  }
  return {
    type: "object",
    additionalProperties: previous?.additionalProperties ?? false,
    properties,
    required,
  };
}

export function sampleValue(schema: JsonSchema): unknown {
  if (schema.enum && schema.enum.length > 0) {
    return schema.enum[0];
  }
  switch (schema.type) {
    case "string":
      return (schema.minLength ?? 0) > 0 ? "sample" : "";
    case "integer":
    case "number":
      return typeof schema.minimum === "number" ? schema.minimum : 0;
    case "boolean":
      return false;
    case "array":
      if ((schema.minItems ?? 0) > 0 && schema.items) {
        return [sampleValue(schema.items)];
      }
      return [];
    case "object": {
      const value: Record<string, unknown> = {};
      for (const [key, property] of Object.entries(schema.properties ?? {})) {
        value[key] = sampleValue(property);
      }
      return value;
    }
    default:
      return null;
  }
}

function isFieldType(value: unknown): value is FieldDraft["type"] {
  return typeof value === "string" && fieldTypes.some((item) => item === value);
}
