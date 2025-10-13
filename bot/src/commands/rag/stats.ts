import { SlashCommandBuilder, ChatInputCommandInteraction } from "discord.js";
import { backendUrl } from "../../config";

interface BackendStatsResponse {
    status: string;
    discord_messages_total?: number;
    discord_messages_for_server?: number;
    notion_documents_total?: number;
    server_id?: string;
}

interface Command {
    data: SlashCommandBuilder;
    execute: (interaction: ChatInputCommandInteraction) => Promise<void>;
}

const numberFormatter = new Intl.NumberFormat();

const command: Command = {
    data: new SlashCommandBuilder()
        .setName("stats")
        .setDescription("Shows backend document counts for Discord messages and Notion pages."),
    async execute(interaction: ChatInputCommandInteraction): Promise<void> {
        await interaction.deferReply({ ephemeral: true });

        try {
            const serverId = interaction.guildId ?? undefined;
            const baseUrl = backendUrl.endsWith("/") ? backendUrl : `${backendUrl}/`;
            const url = new URL("stats", baseUrl);
            if (serverId) {
                url.searchParams.set("server_id", serverId);
            }

            const response = await fetch(url);
            if (!response.ok) {
                await interaction.editReply(`❌ Failed to fetch stats from backend: HTTP ${response.status}`);
                return;
            }

            const data = await response.json() as BackendStatsResponse;
            if (data.status !== "success") {
                await interaction.editReply("❌ Backend returned an error while retrieving stats.");
                return;
            }

            const totalDiscord = data.discord_messages_total ?? 0;
            const serverDiscord = data.discord_messages_for_server ?? totalDiscord;
            const notionDocs = data.notion_documents_total ?? 0;

            const lines = [
                "📊 **Backend Stats**",
                `- Discord messages (total): ${numberFormatter.format(totalDiscord)}`,
            ];

            if (interaction.guild && data.discord_messages_for_server !== undefined) {
                lines.push(`- Discord messages for this server: ${numberFormatter.format(serverDiscord)}`);
            }

            lines.push(`- Notion documents: ${numberFormatter.format(notionDocs)}`);

            await interaction.editReply(lines.join("\n"));
        } catch (error) {
            console.error("Error fetching backend stats:", error);
            await interaction.editReply("❌ An unexpected error occurred while fetching stats.");
        }
    },
};

module.exports = command;
