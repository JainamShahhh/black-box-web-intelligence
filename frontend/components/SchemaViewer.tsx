'use client';

import { useState } from 'react';
import { ChevronRight, ChevronDown, Hash, Type, List, ToggleLeft, Calendar, FileJson } from 'lucide-react';

interface SchemaViewerProps {
    schema: Record<string, any>;
    title?: string;
    method?: string;
    endpoint?: string;
}

const TYPE_ICONS: Record<string, React.ElementType> = {
    string: Type,
    integer: Hash,
    number: Hash,
    boolean: ToggleLeft,
    array: List,
    object: FileJson,
};

const TYPE_COLORS: Record<string, string> = {
    string: 'text-green-400',
    integer: 'text-blue-400',
    number: 'text-blue-400',
    boolean: 'text-purple-400',
    array: 'text-yellow-400',
    object: 'text-cyan-400',
};

function SchemaProperty({
    name,
    schema,
    required = false,
    depth = 0
}: {
    name: string;
    schema: any;
    required?: boolean;
    depth?: number;
}) {
    const [expanded, setExpanded] = useState(depth < 2);
    const type = schema?.type || 'any';
    const hasChildren = type === 'object' && schema.properties;
    const isArray = type === 'array';

    const TypeIcon = TYPE_ICONS[type] || FileJson;
    const typeColor = TYPE_COLORS[type] || 'text-slate-400';

    return (
        <div className="text-sm">
            <div
                className={`flex items-center gap-2 py-1 px-2 rounded hover:bg-slate-700/30 ${hasChildren || isArray ? 'cursor-pointer' : ''}`}
                style={{ paddingLeft: `${depth * 16 + 8}px` }}
                onClick={() => (hasChildren || isArray) && setExpanded(!expanded)}
            >
                {(hasChildren || isArray) && (
                    expanded ? <ChevronDown className="w-3 h-3 text-slate-500" /> : <ChevronRight className="w-3 h-3 text-slate-500" />
                )}
                {!hasChildren && !isArray && <span className="w-3" />}

                <TypeIcon className={`w-3.5 h-3.5 ${typeColor}`} />

                <span className="text-slate-200 font-mono">{name}</span>

                {required && (
                    <span className="text-red-400 text-xs">*</span>
                )}

                <span className={`text-xs ${typeColor}`}>{type}</span>

                {schema.description && (
                    <span className="text-slate-500 text-xs truncate ml-2">
                        — {schema.description}
                    </span>
                )}
            </div>

            {expanded && hasChildren && (
                <div>
                    {Object.entries(schema.properties).map(([propName, propSchema]: [string, any]) => (
                        <SchemaProperty
                            key={propName}
                            name={propName}
                            schema={propSchema}
                            required={schema.required?.includes(propName)}
                            depth={depth + 1}
                        />
                    ))}
                </div>
            )}

            {expanded && isArray && schema.items && (
                <div className="border-l border-slate-700 ml-4">
                    <SchemaProperty
                        name="[item]"
                        schema={schema.items}
                        depth={depth + 1}
                    />
                </div>
            )}
        </div>
    );
}

export default function SchemaViewer({ schema, title, method, endpoint }: SchemaViewerProps) {
    const [showRaw, setShowRaw] = useState(false);

    if (!schema || Object.keys(schema).length === 0) {
        return (
            <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700 text-center">
                <FileJson className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-slate-500 text-sm">No schema available</p>
            </div>
        );
    }

    return (
        <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <FileJson className="w-5 h-5 text-cyan-400" />
                    {method && (
                        <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs font-mono uppercase">
                            {method}
                        </span>
                    )}
                    {endpoint && (
                        <span className="text-slate-300 font-mono text-sm">{endpoint}</span>
                    )}
                    {title && !endpoint && (
                        <span className="text-slate-200 font-medium">{title}</span>
                    )}
                </div>
                <button
                    onClick={() => setShowRaw(!showRaw)}
                    className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded hover:bg-slate-600 transition-colors"
                >
                    {showRaw ? 'Tree' : 'Raw'}
                </button>
            </div>

            {/* Content */}
            <div className="p-4 max-h-96 overflow-y-auto">
                {showRaw ? (
                    <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap">
                        {JSON.stringify(schema, null, 2)}
                    </pre>
                ) : (
                    <div>
                        {schema.properties ? (
                            Object.entries(schema.properties).map(([name, propSchema]: [string, any]) => (
                                <SchemaProperty
                                    key={name}
                                    name={name}
                                    schema={propSchema}
                                    required={schema.required?.includes(name)}
                                />
                            ))
                        ) : (
                            <SchemaProperty name="root" schema={schema} />
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
