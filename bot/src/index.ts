// Require the necessary discord.js classes
import fs from "node:fs";
import path from "node:path";
import { Client, Collection, Events, GatewayIntentBits, Partials, ChatInputCommandInteraction, MessageContextMenuCommandInteraction, Message, PartialMessage } from "discord.js";
import { token, clientId } from "./config";
import { deleteMessage, updateMessage, uploadMessage, messageToJson, isMessageValid } from "./utils/messageUtils";
import { concatResponse, queryRAG } from "./utils/queryUtils";

// Define types for our command structure
interface Command {
    data: {
        name: string;
        [key: string]: any;
    };
    execute: (interaction: ChatInputCommandInteraction | MessageContextMenuCommandInteraction) => Promise<void>;
}

// Extend the Client interface to include our commands collection
declare module "discord.js" {
    export interface Client {
        commands: Collection<string, Command>;
    }
}

// Create a new client instance
const client = new Client({ 
    intents: [
        GatewayIntentBits.Guilds, 
        GatewayIntentBits.GuildMessages, 
        GatewayIntentBits.GuildMessageReactions, 
        GatewayIntentBits.MessageContent, 
    ],
    partials: [
        Partials.Message,
        Partials.Channel,
        Partials.Reaction,
    ]
});

client.commands = new Collection<string, Command>();

const foldersPath = path.join(__dirname, "commands");
const commandFolders = fs.readdirSync(foldersPath);

for (const folder of commandFolders) {
    const commandsPath = path.join(foldersPath, folder);
    const commandFiles = fs.readdirSync(commandsPath).filter(file => file.endsWith(".js") || (file.endsWith(".ts") && !file.endsWith(".d.ts")));
    for (const file of commandFiles) {
        const filePath = path.join(commandsPath, file);
        const command = require(filePath) as Command;
        // Set a new item in the Collection with the key as the command name and the value as the exported module
        if ("data" in command && "execute" in command) {
            client.commands.set(command.data.name, command);
        } else {
            console.log(`[WARNING] The command at ${filePath} is missing a required "data" or "execute" property.`);
        }
    }
}

client.on(Events.InteractionCreate, async (interaction) => {
    if (!interaction.isChatInputCommand() && !interaction.isMessageContextMenuCommand()) return;

    const command = interaction.client.commands.get(interaction.commandName);

    if (!command) {
        console.error(`No command matching ${interaction.commandName} was found.`);
        return;
    }

    try {
        await command.execute(interaction);
    } catch (error) {
        console.error(error);
        if (interaction.replied || interaction.deferred) {
            await interaction.followUp({ content: "There was an error while executing this command!", ephemeral: true });
        } else {
            await interaction.reply({ content: "There was an error while executing this command!", ephemeral: true });
        }
    }
});


// When the client is ready, run this code (only once)
// We use 'c' for the event parameter to keep it separate from the already defined 'client'
client.once(Events.ClientReady, (c) => {
    console.log(`Ready! Logged in as ${c.user.tag}`);
});

// when a message is sent, upload it to vector database
client.on(Events.MessageCreate, async (message: Message) => {
    // Skip if no author (system messages, webhooks, etc.)
    if (!isMessageValid(message)) return;
    
    const success = await uploadMessage(message);
    if (!success) {
        console.warn(`Failed to upload message ${message.id} to vector database`);
    }
});

// when a message is edited, upload it to vector database
client.on(Events.MessageUpdate, async (oldMessage: Message | PartialMessage, newMessage: Message | PartialMessage) => {
    if (!isMessageValid(oldMessage)) return;
    
    // if the message was sent before the bot started, oldMessage will be partial
    if (oldMessage.partial) {
        try {
            await oldMessage.fetch();
        } catch (error) {
            console.log('Something went wrong when fetching the message:', error);
            return;
        }
    }

    // Only upload if we have a complete new message
    if (!newMessage.partial) {
        const success = await updateMessage(oldMessage as Message, newMessage as Message);
        if (!success) {
            console.warn(`Failed to upload updated message ${newMessage.id} to vector database`);
        }
    }
});

// when message is deleted, remove it from vector db
client.on(Events.MessageDelete, async (message: Message | PartialMessage) => {
    if (!isMessageValid(message)) return;

    const success = deleteMessage(message.id);
    if (!success) {
        console.warn(`Failed to remove message ${message.id} from vector database`);
    }

    return;
});

// Log in to Discord with your client's token
client.login(token);
