import { SlashCommandBuilder, ChatInputCommandInteraction, ChannelType, TextChannel, Collection, Message, FetchMessagesOptions } from 'discord.js';
import { uploadMessages } from '../../utils/messageUtils';

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

        const channelId = interaction.channelId;
        const replyId = await interaction.fetchReply().then(msg => msg.id);
        const replyMessage = await interaction.channel?.messages.fetch(replyId);

        try {
            // Get all text channels
            const channels = guild.channels.cache.filter(
                channel => channel.type === ChannelType.GuildText
            ) as Collection<string, TextChannel>;

            await interaction.editReply(`🔍 Found ${channels.size} text channels. Starting export...`);
            const replyId = await interaction.fetchReply().then(msg => msg.id);

            let totalMessages = 0;
            let processedChannels = 0;

            const messageList: Message[] = [];

            const processingEmoji = "<a:processing:1427404300941918209>";

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
                            // Skip bot messages
                            if (message.author.bot) continue;

                            totalMessages++;
                            channelMessages++;

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

            await interaction.editReply(`${processingEmoji} Exporting ${totalMessages} messages from ${processedChannels} channels...`);

            const BATCH_SIZE = 1000;
            const totalBatches = Math.ceil(messageList.length / BATCH_SIZE);

            let uploadSuccess = true;

            // During large imports, the 15 minute timer for interaction replies may be exceeded.
            // Switch to fetching and editing the original reply message directly.

            for (let batchIndex = 0; batchIndex < totalBatches; batchIndex++) {
                const start = batchIndex * BATCH_SIZE;
                const batch = messageList.slice(start, start + BATCH_SIZE);
                const success = await uploadMessages(batch);

                if (!success) {
                    uploadSuccess = false;
                    break;
                }

                
                // await interaction.editReply(
                //     `${processingEmoji} Exporting ${messageList.length} messages from ${processedChannels} channels...\n` +
                //     `📦 Uploaded batches: ${batchIndex + 1}/${totalBatches}`
                // );

                const replyMessage = await interaction.channel?.messages.fetch(replyId);
                if (replyMessage) {
                    await replyMessage.edit(
                        `${processingEmoji} Exporting ${messageList.length} messages from ${processedChannels} channels...\n` +
                        `📦 Uploaded batches: ${batchIndex + 1}/${totalBatches}`
                    );
                }

                // avoid overloading backend
                await new Promise(resolve => setTimeout(resolve, 100));
            }

            
            if (uploadSuccess) {
              await replyMessage?.edit(
                `🎉 **Export Complete!**\n\n` +
                `📊 **Summary:**\n` +
                `• Channels processed: ${processedChannels}/${channels.size}\n` +
                `• Total messages found: ${totalMessages}\n`
                );
            } else {
              await replyMessage?.edit('❌ An error occurred during export. Check console for details.');
            }

        } catch (error) {
            console.error('Error during export:', error);
            await replyMessage?.edit(`❌ An error occurred during export.\n -# ${error}`);
        }
    },
};

module.exports = command;
