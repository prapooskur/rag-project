import { SlashCommandBuilder, ChatInputCommandInteraction, SlashCommandOptionsOnlyBuilder } from 'discord.js';
import { queryRAG, concatResponse } from '../../utils/queryUtils';

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
        
        if (!query) {
            await interaction.editReply('Query is required.');
            return;
        }

        try {
            const result = await queryRAG({
                query: query,
                serverId: interaction.guildId || ''
            });

            if (!result.success) {
                await interaction.editReply(`Error querying RAG agent:\n-# ${result.error}`);
                return;
            }

            if (!result.data) {
                await interaction.editReply('No response from RAG agent.');
                return;
            }

            const formattedResponse = concatResponse(result.data);
            await interaction.editReply(formattedResponse);
            
        } catch (error) {
            console.error(error);
            await interaction.editReply(`Error querying RAG agent:\n-# ${error}`);
        }
    },
};

module.exports = command;
