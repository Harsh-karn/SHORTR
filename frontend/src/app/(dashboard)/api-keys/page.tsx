"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { Key, Plus, Trash2, Copy, Check, Eye, EyeOff } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type APIKey = {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
};

export default function ApiKeysPage() {
  const { getToken } = useAuth();
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchKeys = async () => {
    try {
      const token = await getToken();
      const res = await fetch("http://localhost:8000/v1/api-keys", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) throw new Error("Failed to fetch API keys");
      const data = await res.json();
      setKeys(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    
    setIsCreating(true);
    setError(null);
    try {
      const token = await getToken();
      const res = await fetch("http://localhost:8000/v1/api-keys", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: newKeyName, scopes: ["read", "write"] }),
      });
      if (!res.ok) throw new Error("Failed to create API key");
      const data = await res.json();
      setNewKeyValue(data.key);
      setNewKeyName("");
      fetchKeys(); // Refresh list
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteKey = async (id: string) => {
    if (!confirm("Are you sure you want to delete this API key? Any applications using it will immediately lose access.")) return;
    try {
      const token = await getToken();
      const res = await fetch(`http://localhost:8000/v1/api-keys/${id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) throw new Error("Failed to delete API key");
      setKeys(keys.filter((k) => k.id !== id));
    } catch (err: any) {
      alert(err.message);
    }
  };

  const copyToClipboard = () => {
    if (newKeyValue) {
      navigator.clipboard.writeText(newKeyValue);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">API Keys</h2>
        <p className="text-muted-foreground mt-2">
          Manage API keys for programmatically interacting with your short links and analytics.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-md bg-destructive/10 text-destructive border border-destructive/20">
          {error}
        </div>
      )}

      {newKeyValue && (
        <div className="bg-primary/5 border border-primary/20 rounded-lg p-6 mb-4 shadow-sm animate-in fade-in slide-in-from-top-4">
          <h3 className="text-lg font-semibold text-primary mb-2 flex items-center gap-2">
            <Key className="w-5 h-5" /> Your New API Key
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            Please copy this key and store it somewhere safe. For security reasons, <strong>we will never show it to you again</strong>.
          </p>
          <div className="flex items-center gap-2 bg-background p-3 rounded-md border font-mono text-sm shadow-inner">
            <span className="flex-1 break-all">{newKeyValue}</span>
            <button
              onClick={copyToClipboard}
              className="p-2 hover:bg-muted rounded-md transition-colors"
              title="Copy to clipboard"
            >
              {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <button
            onClick={() => setNewKeyValue(null)}
            className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors w-full"
          >
            I have saved my key
          </button>
        </div>
      )}

      <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
        <div className="p-6 border-b flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-muted/20">
          <h3 className="text-lg font-medium">Active API Keys</h3>
          <form onSubmit={handleCreateKey} className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Key Name (e.g., Production API)"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              className="h-10 px-3 py-2 rounded-md border bg-background text-sm min-w-[250px] focus:outline-none focus:ring-2 focus:ring-primary/50"
              maxLength={50}
              required
            />
            <button
              type="submit"
              disabled={isCreating || !newKeyName.trim()}
              className="h-10 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 whitespace-nowrap"
            >
              <Plus className="w-4 h-4" />
              {isCreating ? "Creating..." : "Create Key"}
            </button>
          </form>
        </div>

        {loading ? (
          <div className="p-12 flex justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : keys.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground flex flex-col items-center">
            <Key className="w-12 h-12 text-muted-foreground/30 mb-4" />
            <p>You don't have any API keys yet.</p>
            <p className="text-sm">Create one above to get started.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground uppercase bg-muted/50 border-b">
                <tr>
                  <th className="px-6 py-4 font-medium">Name</th>
                  <th className="px-6 py-4 font-medium">Key Prefix</th>
                  <th className="px-6 py-4 font-medium">Created</th>
                  <th className="px-6 py-4 font-medium">Last Used</th>
                  <th className="px-6 py-4 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {keys.map((key) => (
                  <tr key={key.id} className="bg-card hover:bg-muted/30 transition-colors group">
                    <td className="px-6 py-4 font-medium">{key.name}</td>
                    <td className="px-6 py-4 font-mono text-muted-foreground">
                      {key.key_prefix}••••••••••••
                    </td>
                    <td className="px-6 py-4 text-muted-foreground">
                      {new Date(key.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-muted-foreground">
                      {key.last_used_at
                        ? new Date(key.last_used_at).toLocaleDateString()
                        : "Never"}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleDeleteKey(key.id)}
                        className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-md transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                        title="Revoke Key"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
