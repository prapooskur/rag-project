import { SlashCommandBuilder, ChatInputCommandInteraction, ChannelType, TextChannel, Collection, Message, FetchMessagesOptions } from 'discord.js';
import { uploadMessage, updateMessage, uploadMessages } from '../../utils';

interface Command {
    data: SlashCommandBuilder;
    execute: (interaction: ChatInputCommandInteraction) => Promise<void>;
}

const command: Command = {
    data: new SlashCommandBuilder()
        .setName('export')
        .setDescription('Exports all messages, in every channel, to backend.'),
    async execute(interaction: ChatInputCommandInteraction): Promise<void> {
        // Defer reply since this will take a while
        await interaction.deferReply();
        
        const guild = interaction.guild;
        if (!guild) {
            await interaction.editReply('❌ This command can only be used in a server!');
            return;
        }

        try {
            // Get all text channels
            const channels = guild.channels.cache.filter(
                channel => channel.type === ChannelType.GuildText
            ) as Collection<string, TextChannel>;

            await interaction.editReply(`🔍 Found ${channels.size} text channels. Starting export...`);

            let totalMessages = 0;
            let processedChannels = 0;

            const messageList: Message[] = [];

            for (const [channelId, channel] of channels) {
                try {
                    await interaction.editReply(
                        `📂 Processing channel: **${channel.name}** (${processedChannels + 1}/${channels.size})\n` +
                        `📊 Total messages processed: ${totalMessages}\n`
                    );

                    // Fetch all messages from the channel
                    let lastMessageId: string | undefined;
                    let channelMessages = 0;

                    while (true) {
                        const fetchOptions: FetchMessagesOptions = { limit: 100 };
                        if (lastMessageId) {
                            fetchOptions.before = lastMessageId;
                        }
                        const messages = await channel.messages.fetch(fetchOptions);

                        if (messages.size === 0) break;

                        // Process messages in batches
                        for (const [messageId, message] of messages) {
                            totalMessages++;
                            channelMessages++;
                            
                            // Skip bot messages if needed (optional)
                            if (message.author.bot) continue;

                            messageList.push(message);


                            // Update progress every 50 messages
                            if (totalMessages % 50 === 0) {
                                await interaction.editReply(
                                    `📂 Processing channel: **${channel.name}** (${processedChannels + 1}/${channels.size})\n` +
                                    `📊 Total messages processed: ${totalMessages}\n`
                                );
                            }
                        }

                        lastMessageId = messages.last()?.id;
                        
                        // Add a small delay to avoid rate limits
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }

                    processedChannels++;
                    console.log(`Processed ${channelMessages} messages from channel: ${channel.name}`);

                } catch (error) {
                    console.error(`Error processing channel ${channel.name}:`, error);
                }
            }

            // Final report
            const uploadSuccess = await uploadMessages(messageList);
            if (uploadSuccess) {
              await interaction.editReply(
                `🎉 **Export Complete!**\n\n` +
                `📊 **Summary:**\n` +
                `• Channels processed: ${processedChannels}/${channels.size}\n` +
                `• Total messages found: ${totalMessages}\n`
            );
            } else {
              await interaction.editReply('❌ An error occurred during export. Check console for details.');
            }

        } catch (error) {
            console.error('Error during export:', error);
            await interaction.editReply('❌ An error occurred during export. Check console for details.');
        }
    },
};

module.exports = command;
