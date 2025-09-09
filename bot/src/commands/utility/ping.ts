import { SlashCommandBuilder, ChatInputCommandInteraction } from 'discord.js';

interface Command {
    data: SlashCommandBuilder;
    execute: (interaction: ChatInputCommandInteraction) => Promise<void>;
}

const command: Command = {
    data: new SlashCommandBuilder()
        .setName('ping')
        .setDescription('Replies with Pong!'),
    async execute(interaction: ChatInputCommandInteraction): Promise<void> {
        await interaction.reply('Pong!');
    },
};

module.exports = command;
