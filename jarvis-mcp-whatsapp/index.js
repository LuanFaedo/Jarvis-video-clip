import pkg from 'whatsapp-web.js';
const { Client, LocalAuth, MessageMedia } = pkg;
import qrcode from 'qrcode-terminal';
import dotenv from 'dotenv';
import chalk from 'chalk';
import fs from 'fs';
import path from 'path';

dotenv.config();

// --- CONFIGURAÇÃO META AI ---
const META_AI_ID = '13135550002@c.us'; 
const imageRequests = new Map(); 

// Variável para controlar a "Cobrança" (Nudge)
let metaAiNudgeTimer = null;

const BRIDGE_FILE = path.resolve('../meta_ai_trigger.json');

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        args: [
            '--no-sandbox', 
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ],
        headless: true
    }
});

client.on('qr', (qr) => qrcode.generate(qr, { small: true }));

// --- FUNÇÃO AUXILIAR DE SEGURANÇA (ESPERA ARQUIVO) ---
async function waitForFile(filePath, timeout = 60000) {
    const startTime = Date.now();
    const fullPath = path.resolve(filePath);
    
    while (Date.now() - startTime < timeout) {
        if (fs.existsSync(fullPath)) {
            const stats = fs.statSync(fullPath);
            if (stats.size > 1024 * 10) { // Mínimo 10KB para ser um vídeo válido
                return fullPath;
            }
        }
        await new Promise(r => setTimeout(r, 1500)); // Espera 1.5s entre checagens
    }
    throw new Error(`Arquivo não pronto após ${timeout/1000}s: ${fullPath}`);
}

client.on('ready', async () => {
    console.log(chalk.green('✅ JARVIS WHATSAPP ONLINE E PRONTO!'));
    
    // ... (restante do código original mantido)

    // --- LOOP DA BRIDGE (IMAGEM E VÍDEO) ---
    setInterval(async () => {
        // 1. Checar por pedidos de GERAÇÃO DE IMAGEM
        if (fs.existsSync(BRIDGE_FILE)) {
            try {
                const rawData = fs.readFileSync(BRIDGE_FILE, 'utf8');
                try { fs.unlinkSync(BRIDGE_FILE); } catch(e){} 
                
                if (!rawData.trim()) return;

                const trigger = JSON.parse(rawData);
                console.log(chalk.magenta(`[BRIDGE] Pedido Imagem: ${trigger.prompt}`));

                imageRequests.set('latest', { 
                    user: trigger.target, 
                    prompt: trigger.prompt,
                    original_user: trigger.original_user_id 
                });
                
                const delay = Math.floor(Math.random() * 3000) + 2000;
                console.log(chalk.yellow(`[BRIDGE] Aguardando ${delay}ms para digitar...`));

                setTimeout(() => {
                    sendToMetaAiWithNudge(trigger.prompt);
                }, delay);

            } catch (e) { console.error(chalk.red(`[BRIDGE ERRO] Loop Imagem: ${e.message}`)); }
        }

        // 2. Checar por pedidos de ENVIO DE VÍDEO PRONTO
        const VIDEO_PUSH_FILE = './video_push.json';
        if (fs.existsSync(VIDEO_PUSH_FILE)) {
            try {
                const rawData = fs.readFileSync(VIDEO_PUSH_FILE, 'utf8');
                let videoData;
                try {
                    videoData = JSON.parse(rawData);
                    // Deleta o gatilho IMEDIATAMENTE para não processar duas vezes
                    fs.unlinkSync(VIDEO_PUSH_FILE); 
                } catch (e) { return; }

                if (!videoData.target || !videoData.path) return;

                console.log(chalk.blue(`[VIDEO PUSH] Aguardando estabilização do arquivo: ${videoData.path}`));

                // FLUXO BLINDADO
                try {
                    const stablePath = await waitForFile(videoData.path, 45000); // 45s de timeout
                    const media = MessageMedia.fromFilePath(stablePath);
                    
                    await client.sendMessage(videoData.target, media, { 
                        caption: videoData.caption || '',
                        sendVideoAsGif: false 
                    });
                    
                    console.log(chalk.green(`[VIDEO PUSH] Vídeo enviado com sucesso para ${videoData.target}`));
                } catch (err) {
                    console.error(chalk.red(`[VIDEO PUSH ERRO] ${err.message}`));
                    await client.sendMessage(videoData.target, `⚠️ O seu vídeo está demorando para processar ou falhou. Verifique se o arquivo existe em: ${videoData.path}`);
                }

            } catch (e) {
                console.error(chalk.red(`[VIDEO PUSH CRITICAL] Loop Vídeo: ${e.message}`));
            }
        }
    }, 2000); // Intervalo de 2s
});

// --- FUNÇÃO DE ENVIO COM COBRANÇA (NUDGE) ---
async function sendToMetaAiWithNudge(prompt) {
    try {
        // Limpa qualquer timer pendente anterior (Reset)
        if (metaAiNudgeTimer) {
            clearTimeout(metaAiNudgeTimer);
            metaAiNudgeTimer = null;
        }

        // Envia o prompt principal
        await client.sendMessage(META_AI_ID, prompt);
        console.log(chalk.green(`[META AI] Prompt enviado: "${prompt.slice(0,30)}..."`));
        console.log(chalk.yellow(`[NUDGE] Preparando 'Ataque Duplo' em 5 segundos...`));

        // ATAQUE DUPLO: Cobra RÁPIDO (5s) para forçar o processamento
        metaAiNudgeTimer = setTimeout(async () => {
            console.log(chalk.yellow(`[NUDGE] Enviando reforço de cobrança...`));
            
            const nudges = ["Gerou a imagem?", "E a foto?", "Conseguiu?", "Manda aí"];
            const chosenNudge = nudges[Math.floor(Math.random() * nudges.length)];
            
            try {
                await client.sendMessage(META_AI_ID, chosenNudge);
                console.log(chalk.green(`[NUDGE] Reforço enviado: "${chosenNudge}"`));
            } catch (err) {
                console.error(chalk.red(`[NUDGE FALHA] ${err.message}`));
            }
            
            metaAiNudgeTimer = null;
        }, 5000); // 5 segundos apenas! 

    } catch (e) {
        console.error(chalk.red(`[ENVIO ERRO] ${e.message}`));
    }
}

const START_TIMESTAMP = Math.floor(Date.now() / 1000);

// --- ESCUTA RESPOSTAS DA META AI ---
client.on('message_create', async msg => {
    try {
        if (msg.timestamp < START_TIMESTAMP) return;

        // Se a Meta AI respondeu (Texto ou Imagem), cancela a cobrança!
        if (msg.from === META_AI_ID) {
            if (metaAiNudgeTimer) {
                clearTimeout(metaAiNudgeTimer);
                metaAiNudgeTimer = null;
                // console.log(chalk.gray(`[NUDGE] Timer cancelado (resposta recebida).`));
            }
        }

        // Se for a Imagem esperada
        if (msg.from === META_AI_ID && msg.hasMedia) {
            console.log(chalk.magenta(`[META AI] Imagem recebida!`));
            
            const requestInfo = imageRequests.get('latest');
            
            if (requestInfo) {
                const media = await msg.downloadMedia();
                await client.sendMessage(requestInfo.user, media, { caption: `🎨 ${requestInfo.prompt}` });
                console.log(chalk.green(`[ZAP] Entregue.`));

                if (requestInfo.original_user) {
                    try {
                        await fetch("http://127.0.0.1:5000/api/receive_image", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                user_id: requestInfo.original_user,
                                image: media.data, 
                                caption: requestInfo.prompt
                            })
                        });
                        console.log(chalk.green(`[APP] Sincronizado.`));
                    } catch (errApi) {}
                }
            }
            return; 
        }
    } catch (e) { console.error(chalk.red(`[META AI] Erro: ${e.message}`)); }
});

// --- INTERAÇÃO NORMAL ---
client.on('message', async msg => {
    try {
        if (!msg || !msg.id || !msg.from) return;
        if (msg.from === 'status@broadcast' || msg.fromMe) return;
        if (msg.from === META_AI_ID) return; 
        if (msg.timestamp < START_TIMESTAMP) return;

        const senderId = msg.from;
        const userText = msg.body;

        let mediaData = null;
        if (msg.hasMedia) {
            try {
                const media = await msg.downloadMedia();
                if (media && (media.mimetype.startsWith('audio/') || msg.type === 'ptt' || media.mimetype.startsWith('image/'))) {
                    mediaData = { data: media.data, mimetype: media.mimetype };
                }
            } catch (e) {}
        }

        // Comando Direto /img
        if (userText.toLowerCase().startsWith('/img ') || userText.toLowerCase().startsWith('/gerar ')) {
            const prompt = userText.replace(/^\/img\s*/i, '').replace(/^\/gerar\s*/i, '').trim();
            imageRequests.set('latest', { user: senderId, prompt: prompt, original_user: senderId });
            
            // HUMANIZAÇÃO + NUDGE
            const delay = Math.floor(Math.random() * 3000) + 2000;
            setTimeout(() => {
                sendToMetaAiWithNudge(prompt);
            }, delay);
            
            await client.sendMessage(senderId, "🎨 Solicitando...");
            return;
        }

        // Cérebro Python
        const brainData = await generateJarvisResponse(userText, senderId, mediaData, senderId);

        if (brainData && brainData.response) {
            let finalText = brainData.response;
            
            // REMOVIDO TRIGGER DUPLICADO - A responsabilidade é da Bridge (JSON)
            finalText = finalText.replace(/\[\[GEN_IMG:.*?\]\]/g, '').trim();

            if (finalText) await client.sendMessage(senderId, finalText);

            if (brainData.audio_parts) {
                for (const part of brainData.audio_parts) {
                    if (part.audio) {
                        const audioMedia = new MessageMedia('audio/mp3', part.audio);
                        await client.sendMessage(senderId, audioMedia, { sendAudioAsVoice: true });
                        await new Promise(r => setTimeout(r, 300));
                    }
                }
            }
        }
    } catch (error) { console.error(chalk.red(`[ERRO] ${error.message}`)); }
});

async function generateJarvisResponse(input, senderId, media = null, chatId = null) {
    try {
        const payload = { text: input, sender: senderId, chat_id: chatId };
        if (media) {
            payload.mimetype = media.mimetype;
            if (media.mimetype.startsWith('image/')) payload.image_data = media.data;
            else payload.audio_data = media.data;
        }

        const response = await fetch("http://127.0.0.1:5000/api/whatsapp", {
            method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
        });
        return await response.json();
    } catch (e) { 
        console.error(chalk.red(`[FALHA CEREBRO] Não foi possível conectar ao Python em 127.0.0.1:5000. Erro: ${e.code || e.message}`));
        return { response: "⚠️ *Erro de Conexão:* O meu cérebro (servidor Python) parece estar desligado ou inacessível. Verifique se o 'app.py' está rodando." }; 
    }
}

client.initialize();
