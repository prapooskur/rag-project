import { Message, PartialMessage } from "discord.js";
import { backendUrl, clientId } from "../config";

async function uploadMessage(message: Message): Promise<boolean> {
    const messageJson = messageToJson(message);
    console.log(JSON.stringify(messageJson))
    try {
        const response = await fetch(backendUrl + "/uploadMessage", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(messageJson),
        });

        if (!response.ok) {
            console.error(`Failed to upload message: ${response.status} ${response.statusText}`);
            return false;
        }

        return true;
    } catch (error) {
        console.error("Error uploading message to backend:", error);
        return false;
    }
}

async function uploadMessages(messageList: Message[]): Promise<boolean> {
    const messageJsonList = messageList.map(messageToJson);
    console.log(JSON.stringify(messageJsonList))
    try {
        const response = await fetch(backendUrl + "/uploadMessages", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(messageJsonList),
        });

        if (!response.ok) {
            console.error(`Failed to upload message list: ${response.status} ${response.statusText}`);
            return false;
        }

        return true;
    } catch (error) {
        console.error("Error uploading message to backend:", error);
        return false;
    }
}

async function updateMessage(oldMessage: Message, newMessage: Message): Promise<boolean> {
    const oldMessageJson = messageToJson(oldMessage);
    const newMessageJson = messageToJson(newMessage);
    try {
        const response = await fetch(backendUrl + "/updateMessage", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ old_message: oldMessageJson, new_message: newMessageJson }),
        });

        if (!response.ok) {
            console.error(`Failed to update message: ${response.status} ${response.statusText}`);
            return false;
        }

        return true;
    } catch (error) {
        console.error("Error updating message to backend:", error);
        return false;
    }
}
    
async function deleteMessage(messageId: string): Promise<boolean> {
    try {
        const response = await fetch(`${backendUrl}/deleteMessage`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({"id": messageId})
        })

        if (!response.ok) {
            console.error(`Failed to delete ${messageId}: ${response.status} ${response.statusText}`);
            return false;
        }

        return true;
    } catch (error) {
        console.error("Error deleting message from backend:", error);
        return false;
    }
}

function messageToJson(message: Message): {
    data: {
        senderNickname: string | null;
        senderUsername: string;
        channelName: string;
        content: string;
    };
    metadata: {
        messageId: string;
        channelId: string;
        serverId: string;
        senderId: string;
        dateTime: string;
    };
} {
    return {
        data: {
            senderNickname: message.member?.nickname || null,
            senderUsername: message.author.username,
            channelName: message.channel.type === 0 || message.channel.type === 2 ? message.channel.name : 'DM',
            content: message.content
        },
        metadata: {
            messageId: message.id,
            channelId: message.channel.id,
            serverId: message.guild?.id || '', // this should never be null (bot does not support DMs)
            senderId: message.author.id,
            dateTime: message.createdAt.toISOString()
        }
    };
}

function isMessageValid(message: Message | PartialMessage): boolean {
    // Skip if no author (system messages, webhooks, etc.)
    if (!message.author) {
        return false;
    }

    // skip slash commands
    if (message.interactionMetadata) return false;

    // Don't process our own bot messages
    if (message.author.id === clientId) return false;

    return true
}

export { uploadMessage, uploadMessages, updateMessage, deleteMessage, messageToJson, isMessageValid };