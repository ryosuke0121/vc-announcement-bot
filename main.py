import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import database  # データベースモジュールをインポート
from datetime import datetime

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Intentsの設定
intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

# Botの初期化
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        # 同時アクセス制御用のロック (guild_id, vc_id) ごと
        self.vc_locks = {}

    def get_vc_lock(self, guild_id: int, vc_id: int):
        """VCごとのロックを取得する"""
        key = (guild_id, vc_id)
        if key not in self.vc_locks:
            self.vc_locks[key] = asyncio.Lock()
        return self.vc_locks[key]

    async def setup_hook(self):
        # データベース初期化
        database.init_db()
        # スラッシュコマンド同期
        await self.tree.sync()
        print("Slash commands synced.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"Botが起動しました！ログイン名: {bot.user}")

# --- Slash Commands ---

@bot.tree.command(name="monitor_setup", description="VC通知設定を追加・更新します")
@app_commands.describe(
    vc_channel="通知するボイスチャンネル",
    notification_channel="通知を送るテキストチャンネル",
    mention_role="メンションするロール"
)
async def monitor_setup(interaction: discord.Interaction, vc_channel: discord.VoiceChannel, notification_channel: discord.TextChannel, mention_role: discord.Role):
    # 権限チェック (管理者のみ実行可能にするなど)
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
        return

    role_id = mention_role.id
    
    database.upsert_config(
        guild_id=interaction.guild_id,
        vc_id=vc_channel.id,
        notification_channel_id=notification_channel.id,
        role_id=role_id
    )

    role_mention_text = mention_role.mention
    await interaction.response.send_message(
        f"設定を保存しました。\n"
        f"通知VC: {vc_channel.name}\n"
        f"通知先: {notification_channel.mention}\n"
        f"ロール: {role_mention_text}",
        ephemeral=True
    )

@bot.tree.command(name="monitor_delete", description="VC通知設定を削除します")
@app_commands.describe(vc_channel="通知を解除するボイスチャンネル")
async def monitor_delete(interaction: discord.Interaction, vc_channel: discord.VoiceChannel):
    # 権限チェック
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
        return

    config = database.get_config(interaction.guild_id, vc_channel.id)
    if not config:
        await interaction.response.send_message(f"{vc_channel.mention} は通知設定されていません。", ephemeral=True)
        return

    database.delete_config(interaction.guild_id, vc_channel.id)
    await interaction.response.send_message(f"{vc_channel.mention} の通知設定を削除しました。", ephemeral=True)

@bot.tree.command(name="show_config", description="現在の通知設定を表示します")
async def show_config(interaction: discord.Interaction):
    # 最適化: サーバーごとの設定のみ取得
    guild_configs = database.get_configs_by_guild(interaction.guild_id)

    if not guild_configs:
        await interaction.response.send_message("このサーバーには設定がありません。", ephemeral=True)
        return

    embed = discord.Embed(title="通知設定一覧", color=discord.Color.blue())
    for conf in guild_configs:
        vc = interaction.guild.get_channel(conf["vc_id"])
        room_name = vc.name if vc else f"Unknown VC ({conf['vc_id']})"
        notif_ch = interaction.guild.get_channel(conf["notification_channel_id"])
        notif_name = notif_ch.name if notif_ch else f"Unknown Channel ({conf['notification_channel_id']})"
        
        val = f"通知先: {notif_name}"
        if conf["role_id"]:
            role = interaction.guild.get_role(conf["role_id"])
            role_name = role.name if role else "Unknown Role"
            val += f"\nメンション: {role_name}"
        
        embed.add_field(name=f"VC: {room_name}", value=val, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="info", description="Botの情報を表示します")
async def info(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 VC通知Bot 情報",
        description="Discord ボイスチャンネルの通話開始/終了を通知するBotです。",
        color=discord.Color.blue()
    )
    embed.add_field(name="📌 バージョン", value="v2.0.0", inline=True)
    embed.add_field(name="📅 最終更新日", value="2025年12月24日", inline=True)
    embed.add_field(name="🔧 主な機能", value=(
        "• VC通話開始時の自動通知\n"
        "• VC通話終了時の自動通知と通話時間表示\n"
        "• ロールメンション機能\n"
        "• 二重送信防止機能（強化版）"
    ), inline=False)
    embed.add_field(name="📝 利用可能なコマンド", value=(
        "`/monitor_setup` - VC通知設定の追加・更新\n"
        "`/monitor_delete` - VC通知設定の削除\n"
        "`/show_config` - 現在の通知設定を表示\n"
        "`/info` - Bot情報を表示"
    ), inline=False)
    embed.set_footer(text="Powered by discord.py")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- Event Listeners ---

@bot.event
async def on_voice_state_update(member, before, after):
    # 最適化: イベントが発生したサーバーの設定のみ取得
    guild_configs = database.get_configs_by_guild(member.guild.id)
    
    if not guild_configs:
        return

    for config in guild_configs:
        target_vc_id = config["vc_id"]
        
        # 必要なデータを取得
        notification_channel_id = config["notification_channel_id"]
        target_role_id = config["role_id"]
        
        target_vc = member.guild.get_channel(target_vc_id)
        notification_channel = member.guild.get_channel(notification_channel_id)
        target_role = member.guild.get_role(target_role_id) if target_role_id else None

        if not target_vc or not notification_channel:
            continue

        # ロックを取得して処理を同期
        lock = bot.get_vc_lock(member.guild.id, target_vc_id)
        
        # 通話開始時の通知
        if before.channel != after.channel and after.channel and after.channel.id == target_vc_id:
            await asyncio.sleep(10)  # 10秒待機

            async with lock:
                members_in_vc = [m for m in target_vc.members if not m.bot]
                
                # データベースから状態を確認して、まだ通知を送っていない場合のみ送信
                if members_in_vc and not database.is_vc_active(member.guild.id, target_vc_id):
                    role_mention = target_role.mention if target_role else ""
                    
                    embed = discord.Embed(
                        title=f"{target_vc.name}で通話が始まりました！",
                        description=f"https://discord.com/channels/{member.guild.id}/{target_vc_id}",
                        color=discord.Color.green()
                    )
                    msg = await notification_channel.send(content=role_mention, embed=embed)
                    
                    # データベースに状態を保存
                    start_time = datetime.now().isoformat()
                    database.set_vc_active(member.guild.id, target_vc_id, start_time, msg.id)
                    
                    # 初期参加者を記録
                    database.clear_participants(member.guild.id, target_vc_id)
                    for m in members_in_vc:
                        database.add_participant(member.guild.id, target_vc_id, m.id, m.display_name)

        # 通話中に参加した人を記録
        if before.channel != after.channel and after.channel and after.channel.id == target_vc_id:
            if database.is_vc_active(member.guild.id, target_vc_id) and not member.bot:
                database.add_participant(member.guild.id, target_vc_id, member.id, member.display_name)
        
        # 通話終了時の通知
        if before.channel and before.channel.id == target_vc_id and before.channel != after.channel:
            await asyncio.sleep(1)

            async with lock:
                members_in_vc = [m for m in target_vc.members if not m.bot]
                
                # データベースから状態を確認して、通話中の場合のみ終了通知を送信
                if len(members_in_vc) == 0 and database.is_vc_active(member.guild.id, target_vc_id):
                    vc_state = database.get_vc_state(member.guild.id, target_vc_id)
                    
                    if vc_state and vc_state['start_time']:
                        start_time = datetime.fromisoformat(vc_state['start_time'])
                        end_time = datetime.now()
                        duration = end_time - start_time
                        
                        # 通話時間を時:分:秒の形式で計算
                        total_seconds = int(duration.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        
                        # 参加者一覧を取得
                        participants = database.get_participants(member.guild.id, target_vc_id)
                        participants_text = "\n".join([f"<@{p['user_id']}>" for p in participants]) if participants else "なし"
                        
                        embed = discord.Embed(
                            title=f"{target_vc.name}での通話が終了しました！",
                            description=f"https://discord.com/channels/{member.guild.id}/{target_vc_id}",
                            color=discord.Color.red()
                        )
                        embed.add_field(name="通話時間", value=duration_str, inline=False)
                        embed.add_field(name="参加者", value=participants_text, inline=False)
                        await notification_channel.send(embed=embed)
                    
                    # データベースの状態をリセット
                    database.set_vc_inactive(member.guild.id, target_vc_id)
                    database.clear_participants(member.guild.id, target_vc_id)

bot.run(TOKEN)