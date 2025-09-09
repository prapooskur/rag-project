import { Message } from "discord.js";
import { backendUrl } from "../config.json";

async function uploadMessage(message: Message): Promise<boolean> {
    console.log(JSON.stringify({ message: message }))
    try {
        const response = await fetch(backendUrl + "/uploadMessage", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: message }),
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
    console.log(JSON.stringify({ messageList: messageList }))
    try {
        const response = await fetch(backendUrl + "/uploadMessages", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ messages: messageList }),
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
    try {
        const response = await fetch(backendUrl + "/updateMessage", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ old: oldMessage, new: newMessage }),
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

export { uploadMessage, uploadMessages, updateMessage };