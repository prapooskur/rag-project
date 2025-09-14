import { backendUrl, guildId } from "../../config.json";

// Interface definitions for query functionality
export interface Source {
    channel: string;
    sender: string | null;
    senderId: string | null;
    content: string;
    channelId: string;
    messageId: string;
    serverId: string;
}

export interface QueryRequest {
    query: string;
    serverId: string;
    similarity_top_k?: number;
    response_type?: "llm" | "retrieval";
}

export interface QueryResponse {
    response?: string;
    sources?: Source[];
    query: string;
    status: string;
    response_type: string;
}

export interface QueryResult {
    success: boolean;
    data?: QueryResponse;
    error?: string;
}

/**
 * Query the RAG backend and format the response for Discord
 * @param queryRequest - The query request parameters
 * @returns Promise containing the formatted response or error
 */
export async function queryRAG(queryRequest: QueryRequest): Promise<QueryResult> {
    try {
        const response = await fetch(backendUrl + "/query", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(queryRequest),
        });

        if (!response.ok) {
            return {
                success: false,
                error: `HTTP ${response.status}: ${response.statusText}`
            };
        }

        const data = await response.json() as QueryResponse;
        
        return {
            success: true,
            data: data
        };

    } catch (error) {
        console.error("Error querying RAG backend:", error);
        return {
            success: false,
            error: error instanceof Error ? error.message : "Unknown error occurred"
        };
    }
}

/**
 * Format sources for Discord display (small text)
 * @param sources - Array of source objects
 * @returns Formatted string for Discord display
 */
export function formatSourcesForDiscord(sources: Source[]): string {
    if (!sources || sources.length === 0) {
        return '';
    }

    return `\n\n**Sources:**\n${sources.map(source => 
        `-# ${source.senderId ? `<@${source.senderId}> @ ` : ''}https://discord.com/channels/${guildId}/${source.channelId}/${source.messageId}: ${source.content.substring(0, 100)}${source.content.length > 100 ? '...' : ''}`
    ).join('\n')}`;
}

/**
 * Combines response and sources.
 * @param queryResponse - The response from the RAG backend
 * @returns Formatted string ready for Discord reply
 */
export function concatResponse(queryResponse: QueryResponse): string {
    const mainResponse = queryResponse.response || 'No response from RAG agent.';
    const sourcesText = formatSourcesForDiscord(queryResponse.sources || []);
    
    return `${mainResponse}${sourcesText}`;
}
