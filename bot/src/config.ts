import dotenv from 'dotenv';
import path from 'path';

// Load environment variables from .env file
dotenv.config({ path: path.join(__dirname, '..', '.env') });

// Validate required environment variables
const requiredEnvVars = ['BOT_TOKEN', 'CLIENT_ID', 'BACKEND_URL'];
const missingEnvVars = requiredEnvVars.filter(varName => !process.env[varName]);

if (missingEnvVars.length > 0) {
    throw new Error(`Missing required environment variables: ${missingEnvVars.join(', ')}`);
}

export const token = process.env.BOT_TOKEN!;
export const clientId = process.env.CLIENT_ID!;
export const guildId = process.env.GUILD_ID || '';
export const backendUrl = process.env.BACKEND_URL!;
