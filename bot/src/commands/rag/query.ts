import { SlashCommandBuilder, ChatInputCommandInteraction, SlashCommandOptionsOnlyBuilder } from 'discord.js';
import { backendUrl, guildId } from '../../../config.json';

interface Source {
    channel: string;
    sender: string | null;
    content: string;
    channelId: string;
    messageId: string;
}

interface Command {
    data: SlashCommandBuilder | SlashCommandOptionsOnlyBuilder;
    execute: (interaction: ChatInputCommandInteraction) => Promise<void>;
}

// todo fixme
const command: Command = {
    data: new SlashCommandBuilder()
        .setName('query')
        .setDescription('Queries RAG agent.')
        .addStringOption(option =>
            option.setName('query')
                .setDescription('The query to send to the RAG agent')
                .setRequired(true)),
    async execute(interaction: ChatInputCommandInteraction): Promise<void> {
        await interaction.deferReply();

        console.log(`${interaction.user.username}: ${interaction.options.getString('query')}`);
        const query = interaction.options.getString('query');
        try {
            const response = await fetch(backendUrl + "/query", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ query: query }),
            });

            const data = await response.json() as { response?: string; sources?: Source[] };
            const sourcesText = data.sources && data.sources.length > 0 
                ? `\n\n**Sources:**\n${data.sources.map(source => 
                    `• **#${source.channel}**: ${source.content.substring(0, 100)}${source.content.length > 100 ? '...' : ''}`
                + ` https://discord.com/channels/${guildId}/${source.channelId}/${source.messageId}`).join('\n')}`
                : '';
            await interaction.editReply(`${data.response}${sourcesText}` || 'No response from RAG agent.');
           
            
        } catch (error) {
            console.error(error);
            await interaction.editReply('Error querying RAG agent.');
        }
    },
};

module.exports = command;
