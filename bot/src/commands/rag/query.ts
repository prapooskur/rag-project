import { SlashCommandBuilder, ChatInputCommandInteraction, SlashCommandOptionsOnlyBuilder, EmbedBuilder } from 'discord.js';
import { queryRAG, formatSourcesForEmbed } from '../../utils/queryUtils';

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
                .setRequired(true))
        .addStringOption(option =>
            option.setName('sources')
                .setDescription('Enabled sources')
                .setRequired(false)
                .addChoices(
                    { name: 'Notion', value: 'notion' },
                    { name: 'Discord', value: 'discord' },
                    { name: 'Both', value: 'both' },
                )),
                
    async execute(interaction: ChatInputCommandInteraction): Promise<void> {
        await interaction.deferReply();

        console.log(`${interaction.user.username}: ${interaction.options.getString('query')}`);
        const query = interaction.options.getString('query');
        
        if (!query) {
            await interaction.editReply('Query is required.');
            return;
        }

        try {
            const enabledSources = interaction.options.getString('sources') || 'both';
            const enable_discord = enabledSources === 'discord' || enabledSources === 'both';
            const enable_notion = enabledSources === 'notion' || enabledSources === 'both';
            const result = await queryRAG({
                query: query,
                serverId: interaction.guildId || '',
                enable_discord: enable_discord,
                enable_notion: enable_notion
            });

            if (!result.success) {
                await interaction.editReply(`Error querying RAG agent\n-# ${result.error}`);
                return;
            }

            if (!result.data) {
                await interaction.editReply('No response from RAG agent.');
                return;
            }

            const formatted_sources = formatSourcesForEmbed(result.data.sources || []);
            const responseEmbed = new EmbedBuilder()
                .setColor(0x0099FF)
                .setTitle('RAGBot Response')
                .setDescription(result.data.response || 'No response')
                .addFields(
                    {
                        name: 'Sources',
                        value: formatted_sources.map(source => 
                            source.length > 195 ? source.substring(0, 200) + '...' : source
                        ).join('\n') || 'No sources'
                    }
                )
                .setTimestamp();

            // const formattedResponse = concatResponse(result.data);
            await interaction.editReply({ embeds: [responseEmbed] });
            
        } catch (error) {
            console.error(error);
            await interaction.editReply(`Error querying RAG agent\n-# ${error}`);
        }
    },
};

module.exports = command;
