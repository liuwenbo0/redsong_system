from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
# 新增: 密码哈希
from werkzeug.security import generate_password_hash, check_password_hash
# 新增: 登录管理
from flask_login import UserMixin
from datetime import datetime
from pytz import timezone
# 创建数据库实例
db = SQLAlchemy()
CST = timezone("Asia/Shanghai")


# --- 关联表 ---

# 1. 用户收藏歌曲 (原有)
user_favorites = db.Table('user_favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('song_id', db.Integer, db.ForeignKey('song.id'), primary_key=True)
)

# 2. (新增) 用户点赞帖子关联表
post_likes = db.Table('post_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('post_id', db.Integer, db.ForeignKey('forum_post.id'), primary_key=True)
)

# 3. (新增) 用户成就关联表
user_achievements = db.Table('user_achievements',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('achievement_id', db.Integer, db.ForeignKey('achievement.id'), primary_key=True)
)

# --- 模型定义 ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # （注意：total_score 改为计算属性，不存储在数据库中）
    @property
    def total_score(self):
        """计算用户总积分：答题积分 + 成就积分"""
        # 答题积分
        quiz_score = db.session.query(func.sum(QuizRecord.score_earned))\
            .filter(QuizRecord.user_id == self.id)\
            .scalar() or 0
        
        # 成就积分
        achievement_score = db.session.query(func.sum(Achievement.points))\
            .join(user_achievements, user_achievements.c.achievement_id == Achievement.id)\
            .filter(user_achievements.c.user_id == self.id)\
            .scalar() or 0
        
        return (quiz_score or 0) + (achievement_score or 0)
    
    # 收藏关系
    favorites = db.relationship('Song', secondary=user_favorites, lazy='dynamic',
                                backref=db.backref('favorited_by', lazy=True))
    # (新增) 点赞关系 - 用户赞过的帖子
    liked_posts = db.relationship('ForumPost', secondary=post_likes, lazy='dynamic',
                                  backref=db.backref('liked_by', lazy='dynamic'))
    # 新增：用户成就关系
    achievements = db.relationship('Achievement', secondary=user_achievements, lazy='dynamic',
                                   backref=db.backref('earned_by', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ForumPost(db.Model):
    """论坛/留言板帖子"""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(CST)
    )
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('posts', lazy='dynamic', overlaps="liked_posts,liked_by"))

    def to_dict(self, current_user=None):
        # 计算点赞数
        like_count = self.liked_by.count()
        # 判断当前用户是否已赞
        is_liked = False
        if current_user and current_user.is_authenticated:
            # 检查当前用户是否在 liked_by 列表中
            # 使用 query 避免加载所有用户
            is_liked = self.liked_by.filter(post_likes.c.user_id == current_user.id).count() > 0

        return {
            'id': self.id,
            'content': self.content,
            'username': self.user.username,
            'user_id': self.user_id, # 返回作者ID，用于前端判断是否显示删除按钮
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M'),
            'like_count': like_count,
            'is_liked': is_liked
        }

# ==============================================================================
# 数据库模型 (Database Models)
# ==============================================================================

class Song(db.Model):
    """歌曲模型"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    artist = db.Column(db.String(100), nullable=False)
    audio_url = db.Column(db.String(200), nullable=True)
    region = db.Column(db.String(50), nullable=True)
    # is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    description = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'audio_url': self.audio_url,
            'region': self.region,
            # 'is_favorite': self.is_favorite,
            'description': self.description
        }

class Article(db.Model):
    """文章模型 - 新增 video_url 字段"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    video_url = db.Column(db.String(255), nullable=True) # 新增：视频链接字段

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'video_url': self.video_url # 新增：在API中返回视频链接
        }

class HistoricalEvent(db.Model):
    """历史事件模型 - 新增详细描述字段"""
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    event_description = db.Column(db.Text, nullable=False)
    detailed_description = db.Column(db.Text, nullable=True) # 新增：详细介绍

    def to_dict(self):
        return {
            'id': self.id, 
            'year': self.year, 
            'event_description': self.event_description,
            'detailed_description': self.detailed_description # 新增：在API中返回
        }
    
class ChatHistory(db.Model):
    """聊天记录模型"""
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(CST)
    )
    # 新增：外键，关联到用户
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    def to_dict(self):
        # 格式化时间戳，使其在API中更友好
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }

# ==============================================================================
# (新增) 答题和成就相关模型
# ==============================================================================

class QuizQuestion(db.Model):
    """竞答题目模型"""
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  # A/B/C/D
    explanation = db.Column(db.Text, nullable=True)  # 解析
    difficulty = db.Column(db.String(20), default='medium')  # easy/medium/hard
    points = db.Column(db.Integer, default=10)  # 本题积分

class QuizRecord(db.Model):
    """答题记录模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)
    user_answer = db.Column(db.String(1), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    score_earned = db.Column(db.Integer, default=0)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(CST)
    )
    
    user = db.relationship('User', backref=db.backref('quiz_records', lazy=True))
    question = db.relationship('QuizQuestion', backref=db.backref('records', lazy=True))

class Achievement(db.Model):
    """成就徽章模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(50), nullable=False)  # 图标代码/图标类名
    category = db.Column(db.String(50), nullable=False)  # 类别：quiz/song/create/forum/total/learn
    condition_type = db.Column(db.String(50), nullable=False)  # 条件类型
    condition_value = db.Column(db.Integer, nullable=False)  # 条件值
    points = db.Column(db.Integer, default=100)  # 解锁成就获得的积分

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'category': self.category,
            'condition_type': self.condition_type,
            'condition_value': self.condition_value,
            'points': self.points
        }

class ArticleView(db.Model):
    """用户浏览文章记录模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(CST))
    
    user = db.relationship('User', backref=db.backref('article_views', lazy=True))
    article = db.relationship('Article', backref=db.backref('views', lazy=True))

class CreatedSong(db.Model):
    """用户创作歌曲记录模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    song_title = db.Column(db.String(200), nullable=False)
    lyrics = db.Column(db.Text, nullable=False)
    style = db.Column(db.String(50), nullable=False)
    audio_url = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(CST))
    
    user = db.relationship('User', backref=db.backref('created_songs', lazy=True))

# ==============================================================================
# (新增) 数据服务层 (Data Service)
# ==============================================================================
class DataService:
    """封装所有数据库查询和操作"""

    def _get_user_favorite_ids(self, user):
        """辅助函数：获取已登录用户的收藏ID集合，用于快速查询"""
        if user.is_authenticated:
            return {song.id for song in user.favorites.all()}
        return set()

    def _add_favorite_status(self, songs_list, favorite_ids):
        """辅助函数：为歌曲字典列表动态添加 'is_favorite' 键"""
        output = []
        for song in songs_list:
            song_dict = song.to_dict()
            song_dict['is_favorite'] = song.id in favorite_ids
            output.append(song_dict)
        return output

    def search_songs(self, query, user) -> list:
        favorite_ids = self._get_user_favorite_ids(user)
        if not query:
            songs = Song.query.all()
        else:
            search_term = f"%{query.lower()}%"
            songs = Song.query.filter(db.or_(Song.title.ilike(search_term), Song.artist.ilike(search_term))).all()
        return self._add_favorite_status(songs, favorite_ids)

    def get_songs_by_region(self, region_name, user) -> list:
        favorite_ids = self._get_user_favorite_ids(user)
        if region_name == "全国":
            songs = Song.query.filter_by(region="全国").all()
        else:
            clean_region_name = region_name.replace('省', '').replace('市', '').replace('自治区', '').replace('维吾尔', '').replace('壮族', '').replace('回族', '')
            songs = Song.query.filter(Song.region.ilike(f"%{clean_region_name}%")).all()
        return self._add_favorite_status(songs, favorite_ids)

    def get_favorite_songs(self, user) -> list:
        # 已登录用户的收藏就是 user.favorites
        songs = user.favorites.all()
        # 收藏页的歌曲 'is_favorite' 默认为 True
        output = []
        for song in songs:
            song_dict = song.to_dict()
            song_dict['is_favorite'] = True
            output.append(song_dict)
        return output

    def toggle_favorite_status(self, user, song) -> dict:
        is_favorited = song in user.favorites.all()
        if is_favorited:
            user.favorites.remove(song)
            db.session.commit()
            song_dict = song.to_dict()
            song_dict['is_favorite'] = False
            return song_dict
        else:
            user.favorites.append(song)
            db.session.commit()
            song_dict = song.to_dict()
            song_dict['is_favorite'] = True
            
            # 检查并解锁成就（新增）
            newly_unlocked = self.check_and_unlock_achievements(user)
            if newly_unlocked:
                song_dict['newly_unlocked'] = [a.to_dict() for a in newly_unlocked]
            
            return song_dict

    def get_articles(self) -> list:
        return [article.to_dict() for article in Article.query.all()]

    def get_historical_events(self) -> list:
        return [event.to_dict() for event in HistoricalEvent.query.order_by(HistoricalEvent.year).all()]

    def add_chat_history(self, user_id, question, answer):
        new_chat = ChatHistory(user_id=user_id, question=question, answer=answer)
        db.session.add(new_chat)
        db.session.commit()
    
    def get_chat_history(self, user_id) -> list:
        history = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.asc()).all()
        return [chat.to_dict() for chat in history]
    
    def clear_chat_history(self, user_id):
        ChatHistory.query.filter_by(user_id=user_id).delete()
        db.session.commit()

    def record_article_view(self, user, article_id):
        """记录用户浏览文章"""
        # 检查是否已经浏览过
        existing = ArticleView.query.filter_by(user_id=user.id, article_id=article_id).first()
        if not existing:
            view = ArticleView(user_id=user.id, article_id=article_id)
            db.session.add(view)
            db.session.commit()
            
            # 检查并解锁成就
            newly_unlocked = self.check_and_unlock_achievements(user)
            return newly_unlocked
        return []
    
    def record_created_song(self, user, song_title, lyrics, style, audio_url=None):
        """记录用户创作的歌曲"""
        song = CreatedSong(
            user_id=user.id,
            song_title=song_title,
            lyrics=lyrics,
            style=style,
            audio_url=audio_url
        )
        db.session.add(song)
        db.session.commit()
        
        # 检查并解锁成就
        newly_unlocked = self.check_and_unlock_achievements(user)
        return newly_unlocked

    def get_forum_posts(self, current_user=None):
        # 获取所有帖子，但在 Python 中进行排序（因为混合了统计属性，SQL排序较复杂）
        # 排序规则：1. 点赞数 (like_count) 降序； 2. 时间 (timestamp) 降序
        posts = ForumPost.query.all()
        # 排序
        posts.sort(key=lambda p: (p.liked_by.count(), p.timestamp), reverse=True)
        
        return [post.to_dict(current_user) for post in posts]

    def add_forum_post(self, user_id, content):
        new_post = ForumPost(user_id=user_id, content=content)
        db.session.add(new_post)
        db.session.commit()
        return new_post.to_dict()
    
    def delete_forum_post(self, post_id, user_id):
        post = ForumPost.query.get(post_id)
        if post and post.user_id == user_id:
            db.session.delete(post)
            db.session.commit()
            return True
        return False
    def toggle_post_like(self, post_id, user):
        post = ForumPost.query.get(post_id)
        if not post: return None
        
        is_liked = post.liked_by.filter(post_likes.c.user_id == user.id).count() > 0
        if is_liked:
            post.liked_by.remove(user)
            liked = False
        else:
            post.liked_by.append(user)
            liked = True
        db.session.commit()
        return {'liked': liked, 'count': post.liked_by.count()}

    # ==================== 答题相关方法 ====================

    def get_random_quiz_questions(self, count=5):
        """随机获取指定数量的题目"""
        all_questions = QuizQuestion.query.all()
        import random
        return random.sample(all_questions, min(count, len(all_questions))) if all_questions else []

    def submit_quiz_answer(self, user, question_id, user_answer):
        """提交答题记录并计算得分"""
        question = QuizQuestion.query.get(question_id)
        if not question:
            return None
        
        is_correct = user_answer.upper() == question.correct_answer.upper()
        score_earned = question.points if is_correct else 0
        
        # 创建答题记录
        record = QuizRecord(
            user=user,
            question=question,
            user_answer=user_answer.upper(),
            is_correct=is_correct,
            score_earned=score_earned
        )
        db.session.add(record)
        
        # （注意：不需要手动增加用户积分，total_score 是计算属性）
        # 积分会通过查询答题记录和成就自动计算
        
        db.session.commit()
        
        # 检查并解锁成就
        newly_unlocked = self.check_and_unlock_achievements(user)
        
        return {
            'success': True,
            'is_correct': is_correct,
            'score_earned': score_earned,
            'correct_answer': question.correct_answer,
            'explanation': question.explanation,
            'current_total_score': user.total_score,
            'newly_unlocked': [a.to_dict() for a in newly_unlocked]
        }

    def get_user_quiz_stats(self, user_id):
        """获取用户答题统计"""
        records = QuizRecord.query.filter_by(user_id=user_id).all()
        total_questions = len(records)
        correct_count = sum(1 for r in records if r.is_correct)
        
        return {
            'total_answered': total_questions,
            'total_correct': correct_count,
            'accuracy': round(correct_count / total_questions * 100, 1) if total_questions > 0 else 0,
            'total_score_from_quiz': sum(r.score_earned for r in records)
        }

    # ==================== 成就相关方法 ====================

    def check_and_unlock_achievements(self, user):
        """检查并解锁用户成就"""
        achievements = Achievement.query.all()
        newly_unlocked = []
        for ach in achievements:
            # 检查是否已解锁
            if ach in user.achievements:
                continue
            
            # 根据成就类型检查条件
            should_unlock = False
            
            if ach.condition_type == 'quiz_correct':
                # 答对指定数量的题目
                correct_count = QuizRecord.query.filter_by(
                    user_id=user.id,
                    is_correct=True
                ).count()
                if correct_count >= ach.condition_value:
                    should_unlock = True
                    
            elif ach.condition_type == 'quiz_streak':
                # 连续答对（这里简化处理，检查总正确率）
                records = QuizRecord.query.filter_by(user_id=user.id).order_by(QuizRecord.timestamp).limit(ach.condition_value).all()
                if all(r.is_correct for r in records) and len(records) >= ach.condition_value:
                    should_unlock = True
                    
            elif ach.condition_type == 'total_score':
                # 总积分达到指定值
                if user.total_score >= ach.condition_value:
                    should_unlock = True
                    
            elif ach.condition_type == 'favorite_songs':
                # 收藏歌曲达到指定数量
                if user.favorites.count() >= ach.condition_value:
                    should_unlock = True
                    
            elif ach.condition_type == 'created_songs':
                # 创作歌曲（这里简化，使用答题作为代理）
                # 实际应该统计创作记录
                quiz_count = QuizRecord.query.filter_by(user_id=user.id).count()
                if quiz_count >= ach.condition_value:
                    should_unlock = True
                    
            elif ach.condition_type == 'chat_messages':
                # 对话消息数达到指定数量
                chat_count = ChatHistory.query.filter_by(user_id=user.id).count()
                if chat_count >= ach.condition_value:
                    should_unlock = True
            
            elif ach.condition_type == 'learn_articles':
                # 浏览AI红歌微课达到指定数量
                view_count = ArticleView.query.filter_by(user_id=user.id).count()
                if view_count >= ach.condition_value:
                    should_unlock = True
            
            elif ach.condition_type == 'create_songs':
                # 创作歌曲达到指定数量
                create_count = CreatedSong.query.filter_by(user_id=user.id).count()
                if create_count >= ach.condition_value:
                    should_unlock = True
            
            elif ach.condition_type == 'forum_posts':
                # 发表帖子达到指定数量
                if user.posts.count() >= ach.condition_value:
                    should_unlock = True
            
            elif ach.condition_type == 'achievement_count':
                # 解锁指定数量的成就
                unlocked_count = user.achievements.count()
                if unlocked_count >= ach.condition_value:
                    should_unlock = True
            
            if should_unlock:
                print(f"[DEBUG] 解锁成就: {ach.name} (条件 {ach.condition_type})")
                if ach not in user.achievements:
                    user.achievements.append(ach)
                    # （注意：不需要手动增加积分，total_score 是计算属性）
                    newly_unlocked.append(ach)
                    print(f"[DEBUG] 成就 {ach.name} 已添加到用户和newly_unlocked列表")
                else:
                    print(f"[DEBUG] 成就 {ach.name} 已存在，跳过")
        if newly_unlocked:
            db.session.commit()
            print(f"[DEBUG] 成功解锁 {len(newly_unlocked)} 个成就，已提交到数据库")
        else:
            print(f"[DEBUG] 本次没有新成就解锁")
        
        return newly_unlocked

    def get_user_achievements(self, user):
        """获取用户已解锁和未解锁的成就"""
        all_achievements = Achievement.query.all()
        user_achievement_ids = {a.id for a in user.achievements}
        
        unlocked = [a for a in all_achievements if a.id in user_achievement_ids]
        locked = [a for a in all_achievements if a.id not in user_achievement_ids]
        
        return {
            'unlocked': [a.to_dict() for a in unlocked],
            'locked': [a.to_dict() for a in locked],
            'unlocked_count': len(unlocked),
            'total_count': len(all_achievements)
        }

    def get_quiz_leaderboard(self, limit=10):
        """获取答题积分排行榜（仅按答题积分排序）"""
        # 计算每个用户的答题积分
        quiz_score_subq = db.session.query(
            QuizRecord.user_id,
            func.sum(QuizRecord.score_earned).label('quiz_score')
        ).group_by(QuizRecord.user_id).subquery()
        
        # 只查询有答题记录的用户，并按答题积分排序
        result = db.session.query(
            User.id,
            User.username,
            func.coalesce(quiz_score_subq.c.quiz_score, 0).label('quiz_score')
        ).join(quiz_score_subq, User.id == quiz_score_subq.c.user_id)\
        .order_by(func.coalesce(quiz_score_subq.c.quiz_score, 0).desc())\
        .limit(limit)\
        .all()
        
        return [{
            'rank': idx + 1,
            'username': r.username,
            'quiz_score': int(r.quiz_score) if r.quiz_score else 0,
            'achievement_count': User.query.get(r.id).achievements.count()
        } for idx, r in enumerate(result)]

    def get_leaderboard(self, limit=10):
        """获取排行榜（使用子查询实现按计算属性排序）"""
        # 计算每个用户的总积分（答题积分 + 成就积分）
        quiz_score_subq = db.session.query(
            QuizRecord.user_id,
            func.sum(QuizRecord.score_earned).label('quiz_score')
        ).group_by(QuizRecord.user_id).subquery()
        
        achievement_score_subq = db.session.query(
            user_achievements.c.user_id,
            func.sum(Achievement.points).label('achievement_score')
        ).join(Achievement, user_achievements.c.achievement_id == Achievement.id)\
            .group_by(user_achievements.c.user_id).subquery()
        
        # 使用外连接获取所有用户，并计算总积分
        result = db.session.query(
            User.id,
            User.username,
            func.coalesce(quiz_score_subq.c.quiz_score, 0).label('quiz_score'),
            func.coalesce(achievement_score_subq.c.achievement_score, 0).label('achievement_score')
        ).outerjoin(quiz_score_subq, User.id == quiz_score_subq.c.user_id)\
        .outerjoin(achievement_score_subq, User.id == achievement_score_subq.c.user_id)\
        .order_by((func.coalesce(quiz_score_subq.c.quiz_score, 0) +
                    func.coalesce(achievement_score_subq.c.achievement_score, 0)).desc())\
        .limit(limit)\
        .all()
        
        return [{
            'rank': idx + 1,
            'username': user.username,
            'total_score': user.total_score,
            'achievement_count': user.achievements.count()
        } for idx, user in enumerate([User.query.get(r.id) for r in result])]



# ==============================================================================
# 数据库初始化函数
# ==============================================================================

def init_db():
    """创建所有表并填充初始数据"""
    db.create_all()

    # 填充歌曲数据
    if not Song.query.first():
        songs_to_add = [
            Song(title="中华人民共和国国歌", artist="群星", region="全国", audio_url="/static/music/guoge.mp3", description="原名《义勇军进行曲》，抗日战争时期电影《风云儿女》的主题曲。"),
            Song(title="东方红", artist="群星", region="陕西", audio_url="static/music/dongfanghong.mp3", description="源自陕北的革命民歌，歌颂了领袖与人民的深厚情感。"),
            Song(title="没有共产党就没有新中国", artist="群星", region="北京", audio_url="static/music/meiyougongchandang.mp3", description="创作于1943年，以朴实的语言和流畅的旋律道出了人民的心声。"),
            Song(title="歌唱祖国", artist="王莘", region="北京", audio_url="static/music/gechangzuguo.mp3", description="创作于1951年国庆节后，被誉为“第二国歌”，表达了对新中国的赞美。"),
            Song(title="社会主义好", artist="中央广播文工团合唱队", region="全国", audio_url="static/music/shehuizhuyi.mp3", description="创作于1957年，歌曲旋律激昂，唱出了人民建设社会主义的热情。"),
            Song(title="团结就是力量", artist="群星", region="河北", audio_url="/static/music/tuanjiejiushililiang.mp3", description="《团结就是力量》由牧虹作词、卢肃作曲，创作于 1943 年抗日战争时期，原为小歌剧《团结就是力量》的主题歌，歌曲以雄壮有力的旋律激励民众团结抗敌，成为凝聚民族力量的经典之作。"),
            Song(title="我们走在大路上", artist="中央广播文工团合唱队", region="辽宁", audio_url="/static/music/womenzouzaidalushang.mp3", description="《我们走在大路上》由劫夫作词作曲，创作于 1963 年，歌曲旋律昂扬向上，展现了中国人民在社会主义道路上阔步前进的坚定信念与豪迈气概。"),
            Song(title="祖国颂", artist="中国人民解放军军乐团", region="北京", audio_url="static/music/zuguosong.mp3", description="《祖国颂》由乔羽作词、刘炽作曲，创作于 1957 年，以恢弘的旋律和深情的歌词，描绘了祖国壮丽山河与人民建设新生活的热烈场景，是歌颂祖国的经典合唱作品。"),
            Song(title="我的祖国", artist="刀郎", region="北京", audio_url="static/music/wodezuguo.mp3", description="《我的祖国》由乔羽作词、刘炽作曲，1956 年作为电影《上甘岭》的插曲首次出现，原版由郭兰英演唱，歌曲以优美的旋律表达了对祖国山河的热爱和对家乡的眷恋，流传广泛。"),
            Song(title="唱支山歌给党听", artist="降央卓玛", region="上海", audio_url="static/music/changzhishangeigeidangting.mp3", description="《唱支山歌给党听》由蕉萍作词、朱践耳作曲，歌词源自雷锋日记中的诗歌，1963 年经谱曲后广为传唱，表达了人民对中国共产党的深厚感情与衷心拥戴。"),
            Song(title="党啊，亲爱的妈妈", artist="金婷婷", region="湖南", audio_url="static/music/dangaqinaidemama.mp3", description="《党啊，亲爱的妈妈》由龚爱书、佘致迪作词，马殿银、周右作曲，创作于 1981 年，歌曲以亲切的口吻将党比作母亲，抒发了对党的感恩与热爱之情。"),
            Song(title="妈妈教我一支歌", artist="殷秀梅", region="全国", audio_url="static/music/mamajiaowoyizhige.mp3", description="《妈妈教我一支歌》由杨涌作词、刘虹作曲，创作于 1982 年，歌曲通过 “妈妈教歌” 的叙事，展现红色基因的代代传承，表达对党的热爱薪火相传。"),
            Song(title="我爱你，中国", artist="殷秀梅", region="广东", audio_url="static/music/woainizhongguo.mp3", description="《我爱你，中国》由瞿琮作词、郑秋枫作曲，1980 年作为电影《海外赤子》的插曲诞生，旋律优美激昂，抒发了海外游子及全体中华儿女对祖国的炽热深情。"),
            Song(title="祖国，慈祥的母亲", artist="殷秀梅", region="全国", audio_url="static/music/zuguocixiangdemuqin.mp3", description="《祖国，慈祥的母亲》由张鸿西作词、陆在易作曲，创作于 1981 年，歌曲以细腻的情感将祖国比作慈祥的母亲，表达了对祖国母亲的深深眷恋与赞美。"),
            Song(title="祖国啊，我永远热爱你", artist="殷秀梅", region="全国", audio_url="static/music/zuguoawoyongyuanreaini.mp3", description="《祖国啊，我永远热爱你》由刘合庄作词、李正作曲，创作于 1982 年，歌曲旋律深情婉转，传递出对祖国永恒不变的热爱与忠诚，具有强烈的感染力。"),
            Song(title="我和我的祖国", artist="李谷一", region="北京", audio_url="/static/music/wohewodezuguo.mp3", description="《我和我的祖国》由张藜作词、秦咏诚作曲，李谷一于 1985 年首唱，是承载国民家国情怀的经典红歌。"),
            Song(title="今天是你生日，中国", artist="周深", region="北京", audio_url="/static/music/jintianshinishengrizhongguo.mp3", description="《今天是你生日，中国》由韩静霆作词、谷建芬作曲，董文华于 1989 年首唱，以真挚情感抒发对祖国生日的祝福。"),
            Song(title="共和国之恋", artist="殷秀梅", region="北京", audio_url="/static/music/gongheguozhilian.mp3", description="《共和国之恋》由刘毅然作词、刘为光作曲，是献给中国科技工作者的赞歌，传递对祖国的深情与奉献精神。"),
            Song(title="大中国", artist="玖月奇迹", region="北京", audio_url="/static/music/dazhongguo.mp3", description="《大中国》由高枫作词作曲并演唱，1995 年发行，以简洁明快的旋律展现对中国大地与民族的热爱。"),
            Song(title="我的中国心", artist="张明敏", region="香港", audio_url="/static/music/wodezhongguoxin.mp3", description="《我的中国心》由黄霑作词、王福龄作曲，张明敏 1984 年春晚演唱后风靡全国，表达海外华人的赤子情怀。"),
            Song(title="中国人", artist="刘德华", region="香港", audio_url="/static/music/zhongguoren.mp3", description="《中国人》由李安修作词、陈耀川作曲，刘德华 1997 年演唱，呼应香港回归，彰显民族自豪感与凝聚力。"),
            Song(title="龙的传人", artist="王力宏", region="台湾", audio_url="/static/music/longdechuanren.mp3", description="歌曲以龙的象征意义为核心，传递民族认同感与文化归属感，旋律悠扬且充满家国情怀。"),
            Song(title="东方之珠", artist="罗大佑", region="香港", audio_url="/static/music/dongfangzhizhu.mp3", description="以抒情的曲风描绘香港的独特魅力，承载着对这片土地的深情与眷恋，是时代记忆中的经典之作。"),
            Song(title="多情的土地", artist="韩磊", region="全国", audio_url="/static/music/duoqingdetudi.mp3", description="歌曲旋律饱含深情，歌颂祖国大地的广袤与富饶，表达了对故土深深的热爱与眷恋。"),
            Song(title="谁不说俺家乡好", artist="阎维文", region="山东", audio_url="/static/music/sheibushuoanjiaxianghao.mp3", description="电影《红日》插曲，以山东民歌的音调，赞美了沂蒙山区的秀美景色和人民的新生活。"),
            Song(title="长城长", artist="董文华", region="北京", audio_url="/static/music/changchengchang.mp3", description="歌曲围绕长城展开，旋律雄浑大气，展现了长城的雄伟壮阔，传递出对祖国山河的自豪与热爱。"),
            Song(title="我们是黄河泰山", artist="彭丽媛", region="山东", audio_url="/static/music/womenshihuanghetaishan.mp3", description="以黄河、泰山为意象，曲调激昂有力，彰显了中华民族坚韧不拔的精神与磅礴的气势。"),
            Song(title="珠穆朗玛", artist="彭丽媛", region="西藏", audio_url="/static/music/zhumulangma.mp3", description="歌曲旋律高亢嘹亮，描绘了珠穆朗玛峰的巍峨壮丽，传递出对雪域高原的敬畏与赞美之情。"),
            Song(title="青藏高原", artist="李娜", region="青海", audio_url="/static/music/qingzanggaoyuan.mp3", description="曲调空灵辽阔，唱出了青藏高原的壮美风光与独特风情，展现了高原的神秘与圣洁。"),
            Song(title="长江之歌", artist="殷秀梅", region="全国", audio_url="/static/music/changjiangzhige.mp3", description="歌曲以长江为歌颂对象，旋律恢弘流畅，展现了长江的奔腾不息与母亲河的哺育之恩，饱含民族自豪感。"),
            Song(title="洪湖水，浪打浪", artist="王玉珍", region="湖北",  audio_url="/static/music/honghushuilangdalang.mp3", description="歌剧《洪湖赤卫队》选曲，描绘了湖北洪湖地区优美的自然风光和军民鱼水情。"),
            Song(title="南泥湾", artist="崔健", region="陕西", audio_url="/static/music/nanniwan.mp3", description="歌曲诞生于抗战时期，旋律轻快活泼，歌颂了八路军三五九旅在南泥湾垦荒屯田、自力更生的奋斗精神。"),
            Song(title="边疆的泉水清又纯", artist="李谷一", region="全国", audio_url="/static/music/bianjiangdequanshuiqingyouchun.mp3", description="曲调清新优美，赞美了边疆泉水的清澈纯净，也象征着边疆军民纯洁真挚的情感与安宁的生活。"),
            Song(title="大海啊故乡", artist="姚璎格", region="全国", audio_url="/static/music/dahaiaguxiang.mp3", description="歌曲以大海为载体，旋律温柔抒情，表达了对故乡的思念之情，以及对大海般宽广胸怀的向往。"),
            Song(title="太湖美", artist="程桂兰", region="江苏", audio_url="/static/music/taihumei.mp3", description="1978年，南京军区政治部前线歌舞团的任红举、龙飞受太湖风光启发，分别作词作曲创作出《太湖美》，歌曲既展现太湖绝美风光，也寓意改革开放初期打破思想束缚的时代内涵。该曲推出程桂兰演唱的苏州方言版本成为经典江南主题歌曲。"),
            Song(title="在那桃花盛开的地方", artist="蒋大为", region="辽宁", audio_url="/static/music/zainataohuashengkaidedifang.mp3", description="邬大为、魏宝贵作词、铁源作曲的《在那桃花盛开的地方》，灵感源自1969年底至1970年初戍边的奉化籍战士王武位在零下40℃环境中思念家乡桃花的事迹，铁源推翻港台流行风格初稿后融入辽东曲调完成创作，1984 年经蒋大为在央视春晚首唱后广为传播，先后6次登上春晚舞台。"),
            Song(title="我爱你，塞北的雪", artist="彭丽媛", region="黑龙江", audio_url="/static/music/woainisaibeidexue.mp3", description="王德作词、刘锡津1980年末在北方冰冷琴房一小时内谱曲的《我爱你，塞北的雪》，融合苏州评弹与东北秧歌等南北音乐素材，以拟人手法描绘塞北风光、寄托深厚家国情怀，1982年经彭丽媛在央视春晚演唱后广为人知，2019年入选“庆祝中华人民共和国成立70周年优秀歌曲100 首”。"),
            Song(title="故乡的云", artist="费翔", region="台湾", audio_url="/static/music/guxiangdeyun.mp3", description="《故乡的云》是由小轩作词、谭健常作曲的经典红歌，1987年费翔在央视春晚的演绎使其传遍全国，歌曲以游子思乡之情承载家国情怀与民族认同，既呼应了改革开放初期的归国潮，也成为凝聚海峡两岸情感的红色文化符号，入选 “庆祝中华人民共和国成立70周年优秀歌曲100首”。"),
            Song(title="草原上升起不落的太阳", artist="吴雁泽", region="内蒙古", audio_url="/static/music/caoyuanshangshengqibuluodetaiyangmp3.mp3", description="由美丽其格写下草原儿女的赤诚，吴雁泽用透亮高亢的嗓音唱遍大江南北，旋律里满是风吹草低的辽阔与热血，既藏着少数民族对祖国的深情告白，更把对党和美好生活的向往唱成了穿越时空的红色共鸣，至今听来仍让人忍不住跟着哼唱。"),
            Song(title="美丽的草原我的家", artist="德德玛", region="内蒙古", audio_url="/static/music/meilidecaoyuanwodejia.mp3", description="《美丽的草原我的家》由火华作词、阿拉腾奥勒作曲，源于对内蒙古草原生活的真实感悟与赞美，经德德玛深情演绎广为流传，以草原美景描绘承载家国情怀，入选 “庆祝中华人民共和国成立70周年优秀歌曲100首”，是兼具民族风情与红色底蕴的经典红歌。"),
            Song(title="月光下的凤尾竹", artist="关牧村", region="云南", audio_url="/static/music/yueguangxiadefengweizhu.mp3", description="关牧村翻唱的经典之作《月光下的凤尾竹》，由倪维德、施光南联手创作，源于改革开放初期的边疆采风经历，借悠扬傣族旋律勾勒幸福图景，凝聚民族情谊与爱国热忱，成为彰显红色底蕴的时代金曲。"),
            Song(title="乌苏里船歌", artist="郭颂", region="黑龙江", audio_url="/static/music/wusulichuange.mp3", description="《乌苏里船歌》创作于1962年，由郭颂、胡小石作词，郭颂、汪云才作曲并经郭颂演唱广为流传，其主曲调改编自赫哲族民间曲调，是为参加 “哈尔滨之夏” 而打磨的作品。歌曲以船歌体裁生动描绘乌苏里江渔猎场景与山河美景，借特色衬词传递赫哲族人民对劳动生活的热爱与幸福心声，兼具浓郁民族风情与红色底蕴。它不仅入选 “庆祝中华人民共和国成立70周年优秀歌曲100首”，还被联合国教科文组织选为国际音乐教材，成为传唱不衰的经典。"),
            Song(title="在那遥远的地方", artist="王洛宾", region="青海", audio_url="/static/music/zainayaoyuandedifang.mp3", description="《在那遥远的地方》是王洛宾1939年赴青海金银滩草原采风时，受藏族姑娘卓玛的灵感启发创作的作品，初稿名为《草原情歌》后更名传唱。歌曲融合哈萨克族、藏族民歌特色与西方七声音阶，以优美旋律和真挚歌词描绘浪漫情愫，更成为藏汉民族团结的象征与东西方文化交流的桥梁。它不仅斩获金唱片特别创作奖等多项荣誉，还随 “嫦娥一号” 探月卫星在太空播放，是兼具红色底蕴与世界影响力的经典之作。"),
            Song(title="吐鲁番的葡萄熟了", artist="关牧村", region="新疆", audio_url="/static/music/tulufandeputaoshule.mp3", description="1977年源于瞿琮新疆边防哨卡体验生活的灵感创作，1978年经关牧村深情演绎广为流传。歌曲以新疆音乐元素与手鼓节奏为基底，讲述维吾尔族姑娘阿娜尔罕与边防战士克里木的爱情故事，将个人思念与家国守护相融。它既获评 “最美城市音乐名片十佳歌曲”，又以浓郁民族风情与红色情怀成为连接边疆与内地、传递爱国热忱的经典之作。"),
            Song(title="阿里山的姑娘", artist="邓丽君", region="台湾", audio_url="/static/music/alishandeguniang.mp3", description="又名《高山青》，是1949年电影《阿里山风云》的主题曲，由邓禹平作词、张彻作曲，邓丽君1978年的演绎使其传遍华语世界。歌曲虽非原生民歌，却融合台湾邹族等原住民音乐元素，以 “高山青，涧水蓝” 勾勒宝岛风光，用 “姑娘美如水、少年壮如山” 赞美当地人民，暗藏着时代背景下的故土情怀与民族联结。它不仅入选 “嫦娥一号” 探月卫星搭载曲目，更成为跨越海峡、传递中华文化认同的经典红歌符号。"),
            Song(title="克拉玛依之歌", artist="吕文科", region="新疆", audio_url="/static/music/kelamayizhige.mp3", description="《克拉玛依之歌》由吕远作词作曲，1959 年经吕文科首唱并迅速传遍全国，是为歌颂克拉玛依油田开发建设而创作的经典曲目。歌曲以质朴歌词勾勒戈壁油田从荒漠到新城的蜕变，用激昂旋律抒发建设者的豪情壮志与对祖国大地的热爱，兼具时代印记与红色底蕴。它不仅见证了新中国工业建设的奋斗历程，更成为凝聚建设者精神、传递家国情怀的传世之作。"),
            Song(title="我为祖国献石油", artist="刘秉义", region="黑龙江", audio_url="/static/music/woweizuguoxianshiyou.mp3", description="《我为祖国献石油》由薛柱国作词、秦咏诚作曲，1964年经刘秉义首唱传遍全国，是为歌颂石油工人奋斗精神而创作的红色经典。歌曲紧扣新中国工业建设热潮，以铿锵旋律和豪迈歌词，展现石油工人战天斗地、扎根边疆的奉献情怀，将个人奋斗与家国发展深度绑定。作为见证国家发展历程、彰显工业建设者爱国热忱的时代赞歌，它成功入选 “庆祝中华人民共和国成立70周年优秀歌曲100首”。"),
            Song(title="众人划桨开大船", artist="付笛声", region="全国", audio_url="/static/music/zhongrenhuajiangkaidachuan.mp3", description="《众人划桨开大船》由魏明伦、王持久作词，陈翔宇作曲1993年经付笛声演唱走红，是契合时代精神的红色经典。歌曲以 “同舟共济” 为核心，用通俗歌词与激昂旋律，传递团结协作、众志成城的奋进力量，将个人担当与集体发展、国家建设紧密相连。作为传唱度极高的时代金曲，它既彰显了凝心聚力的民族精神，更成为激励人们携手奋进、共筑家国梦想的红色符号。"),
            Song(title="长大后我就成了你", artist="宋祖英", region="全国", audio_url="/static/music/zhangdahouwojiuchengleni.mp3", description="《长大后我就成了你》由宋青松作词、王佑贵作曲，1994年经宋祖英深情演绎广为流传，是歌颂人民教师的经典红歌。歌曲以质朴真挚的歌词、舒缓动人的旋律，勾勒教师教书育人的奉献场景，传递对恩师的崇敬与传承教育初心的情怀。既入选 “中国改革开放30年优秀歌曲”，更成为连接师生情感、彰显教育工作者家国担当的时代赞歌。"),
            Song(title="打靶归来", artist="贾世骏", region="全国", audio_url="/static/music/dabaguilai.mp3", description="《打靶归来》由牛宝源、王永泉作词，王永泉作曲，1960 年源于部队实战化训练场景创作 —— 当时王永泉深入军营体验生活，目睹战士们打完靶后踏着夕阳、唱着军歌归来的昂扬景象，结合部队练兵热潮写下这首作品，经贾世骏首唱后迅速传遍全国。歌曲以明快节奏、直白歌词再现战士打靶后的喜悦与豪迈，尽显军人保家卫国的赤诚与青春朝气。"),
            Song(title="军港之夜", artist="苏小明", region="全国", audio_url="/static/music/jungangzhiye.mp3", description="《军港之夜》由马金星作词、刘诗召作曲，1980词作者马金星深入军港体验水兵生活，捕捉夜晚军港宁静祥和与水兵坚守岗位的动人场景，经苏小明温柔演绎后迅速传遍全国。歌曲以舒缓悠扬的旋律、质朴写实的歌词，勾勒军港夜色与水兵的思乡之情，将个人奉献与家国守护巧妙融合，打破了以往军旅歌曲的激昂风格。作为开创抒情军旅歌曲先河的经典，它既入选 “中国改革开放30年优秀歌曲”，更成为传递军民鱼水情与爱国戍边情怀的红色符号。"),
            Song(title="十五的月亮", artist="董文华", region="全国", audio_url="/static/music/shiwudeyueliang.mp3", description="《十五的月亮》是1984年创作的经典红歌，由石祥作词、铁源和徐锡宜作曲，董文华的深情演唱让它传遍全国。歌曲聚焦边防战士和军属，用大家熟悉的中秋圆月当纽带，既唱出了战士对家乡亲人的思念，也赞颂了军属背后的默默支持。它把个人的牵挂和国家的安宁绑在一起，还入选了 “庆祝中华人民共和国成立70周年优秀歌曲100首”，成了传递爱国情怀和家庭温情的经典之作。"),
            Song(title="望星空", artist="董文华", region="全国", audio_url="/static/music/wangxingkong.mp3", description="《望星空》由石祥作词、铁源作曲，1984 年与《十五的月亮》形成 “军旅抒情姊妹篇” 创作 —— 聚焦边防战士与军属的双向思念，借 “星空” 为情感载体，经董文华温柔演绎广为流传。歌曲用通俗直白的歌词、舒缓深情的旋律，既唱出战士遥望星空思念亲人的牵挂，也传递军属守望家国的理解与支持，将个人柔情与爱国担当自然融合。作为经典红色抒情曲目，它既贴合大众情感共鸣，更成为见证军民同心、传递家国情怀的传世之作。"),
            Song(title="血染的风采", artist="董文华", region="全国", audio_url="/static/music/xuerandefengcai.mp3", description="由陈哲作词、苏越作曲，1986 年为致敬对越自卫反击战中的英烈与参战将士创作，经董文华深情演绎后传遍全国。歌曲用直白质朴的语言、深情婉转的旋律，既唱出了战士们为国家奉献的赤诚，也传递了军属对亲人的牵挂与敬意，道尽了 “牺牲与守护” 的家国情怀。"),
            Song(title="当兵的人", artist="刘斌", region="全国", audio_url="/static/music/dangbingderen.mp3", description="《当兵的人》是1994年创作的红色经典，由王晓岭作词、臧云飞作曲，刘斌的豪迈演唱让它火遍全国。歌曲源于对军人身份的深度刻画，聚焦 “当兵的人” 与普通百姓的异同 —— 既有着和大家一样的亲情牵挂，更肩负着保家卫国的特殊使命。歌词直白接地气，旋律激昂有力量，既唱出了军人的责任与担当，也传递了他们无私奉献的爱国情怀，还入选了 “庆祝中华人民共和国成立70周年优秀歌曲100首”。"),
            Song(title="一二三四歌", artist="阎维文", region="全国", audio_url="/static/music/yiersansige.mp3", description="《一二三四歌》是1993年创作的军旅红色经典，由石顺义作词、臧云飞作曲，阎维文的激昂演唱让它广为流传。歌曲紧扣军营训练生活，灵感源于战士们日常队列训练、操练时的口号与节奏，用简单有力的 “一二三四” 贯穿始终。旋律明快有气势，歌词直白接地气，既唱出了军人的热血豪情与昂扬斗志，也传递了保家卫国的赤诚之心，还入选了 “庆祝中华人民共和国成立70周年优秀歌曲100首”。"),
            Song(title="说句心里话", artist="阎维文", region="全国", audio_url="/static/music/shuojuxinlihua.mp3", description="1989年诞生的《说句心里话》，是石顺义作词、士心作曲的军旅红歌，经阎维文的动情演绎火遍大江南北。歌曲扎根军营真实生活，词作者通过实地采风，读懂了战士们的内心 —— 既有对家乡亲人的牵挂思念，更有守护家国的坚定信念，用朴实无华的语言道尽军人的柔情与担当。它旋律舒缓却藏着力量，既拉近了军民之间的距离，又传递着真挚的爱国情怀，还成功入选 “庆祝中华人民共和国成立70周年优秀歌曲100首”。"),
            Song(title="小白杨", artist="阎维文", region="新疆", audio_url="/static/music/xiaobaiyang.mp3", description="《小白杨》是1984年创作的军旅红歌，由梁上泉作词、士心作曲，阎维文的深情演唱让它广为流传。歌曲灵感源于真实故事 —— 一位新疆边防战士把家乡带来的白杨树苗栽在哨所旁，树苗伴着战士们的坚守茁壮成长，成为戍边精神的象征。歌词朴实直白，旋律悠扬动人，既唱出了战士对家乡的思念，更传递了他们扎根边疆、守护家国的赤诚，还入选了 “庆祝中华人民共和国成立70周年优秀歌曲100首”。"),
            Song(title="情深意长", artist="邓玉华", region="四川", audio_url="/static/music/qingshenyichang.mp3", description="《情深意长》是     1964年音乐舞蹈史诗《东方红》中的经典曲目，由王印泉作词、臧东升作曲，邓玉华的深情演绎让它广为流传。歌曲灵感源于红军长征过凉山时，与彝族群众结下的鱼水深情，用悠扬的彝族民歌旋律和真挚歌词，再现了民族团结的动人场景。它既唱出了各族人民对红军的爱戴，也传递了患难与共的家国情怀，还入选了 “庆祝中华人民共和国成立70周年优秀歌曲100首”。"),
            Song(title="革命人永远是年轻", artist="中央乐团合唱队", region="全国", audio_url="/static/music/gemingrenyongyuanshinianqing.mp3", description="《革命人永远是年轻》是1949年创作的经典红歌，由劫夫作词作曲，中央乐团合唱队的激昂演绎让它长久流传。歌曲诞生于革命胜利前夕，灵感源于革命者坚定的理想信念与蓬勃朝气，紧扣时代脉搏歌颂奋斗精神。旋律明快昂扬，歌词铿锵有力，既唱出了革命人永葆青春的精神风貌，也传递了坚守信仰、砥砺前行的家国情怀，还入选了 “庆祝中华人民共和国成立70周年优秀歌曲100首”。"),
            Song(title="九九艳阳天", artist="叶矛", region="江苏", audio_url="/static/music/jiujiuyanyangtian.mp3", description="《九九艳阳天》是1957年电影《柳堡的故事》的插曲，由胡石言、黄宗江作词，高如星作曲，叶矛与廖莎的对唱版本让它广为流传。歌曲创作源于江南水乡的春日场景，紧扣影片中军民之间纯真的情感，用清新明快的旋律和质朴直白的歌词，勾勒出九九艳阳天里的美好意境。它既唱出了年轻人的真挚情愫，也传递了军民同心的温情，还入选了 “中国电影百年百首金曲”，成为跨越时代的经典红歌。"),
            Song(title="草原之夜", artist="朱崇懋", region="内蒙古", audio_url="/static/music/caoyuanzhiye.mp3", description="《草原之夜》是1959年电影《绿色的原野》的插曲，由张加毅作词、田歌作曲，朱崇懋的深情演唱让它成为传世经典。歌曲创作源于新疆伊犁草原的夜色场景 —— 词作者实地采风时，被草原宁静的夜晚、牧民的淳朴生活打动，以悠扬的旋律和诗意的歌词，勾勒出草原之夜的静谧美好与牧民的真挚情怀。它既有着浓郁的民族风情，又传递了对家乡、对生活的热爱，还被誉为 “中国第一首流行歌曲”，成为跨越时代的红色经典。"),
            Song(title="花儿为什么这样红", artist="塔吉克族民歌", region="新疆", audio_url="/static/music/huaerweishenmezheyanghong.mp3", description="《花儿为什么这样红》是源于塔吉克族民歌《古丽碧塔》的经典红歌，1961 年由雷振邦为电影《冰山上的来客》改编创作，朱逢博等歌手的演绎让它广为流传。歌曲以花为喻，用充满民族风情的旋律和真挚歌词，赞美爱情与友谊，也传递了边防战士的坚定信念，还入选了 “庆祝中华人民共和国成立70周年优秀歌曲100首”。"),
            Song(title="我们的生活充满阳光", artist="于淑珍", region="全国",audio_url="/static/music/womendeshenghuochongmanyangguang.mp3", description="1979 年吕远、唐诃作曲，电影《甜蜜的事业》主题曲，入选国庆 70 周年优秀歌曲, 传递对美好生活的憧憬，旋律轻快洋溢着积极向上的正量。 "),
            Song(title="年轻的朋友来相会", artist="张振富", region="全国",audio_url="/static/music/nianqingdepengyoulaixianghui.mp3",description="1980 年谷建芬作曲，张枚同作词，获改革开放 40 年流行金曲奖。歌颂青春友谊与时代朝气，是激励年轻人奋进的经典金曲。"),
            Song(title="少年壮志不言愁", artist="刘欢", region="全国" ,audio_url="/static/music/shaonianzhuangzhibuyanchou.mp3",description="1987 年雷蕾作曲，林汝为作词，电视剧《便衣警察》主题曲。彰显少年人追梦的执着与担当，歌词励志、旋律激昂动人。"),
            Song(title="亚洲雄风", artist="刘欢", region="全国",audio_url="/static/music/yazhouxiongfeng.mp3 ", description="1990 年徐沛东作曲，张藜作词，为北京亚运会创作的宣传曲。展现亚洲风采与团结力量，节奏铿锵有力，充满昂扬斗志。"),

            Song(title="爱我中华", artist="宋祖英", region="全国",audio_url="/static/music/aiwozhonghua.mp3", description="1991 年徐沛东作曲，乔羽作词，展现民族团结，获多项音乐奖项。抒发对祖国的深厚热爱与自豪，旋律恢弘，传递民族凝聚力。"),
            Song(title="父老乡亲", artist="彭丽媛", region="全国",audio_url="/static/music/fulaoxiangqin.mp3 ", description="1990 年王锡仁作曲，石顺义词，表达对乡亲的感恩，传唱度极高。饱含对乡亲们的感恩与眷恋，情感真挚，唱出质朴人间温情。"),
            Song(title="烛光里的妈妈", artist="毛阿敏", region="全国",audio_url="/static/music/aiwozhonghua.mp3", description=""),
            Song(title="夕阳红", artist="佟铁鑫", region="全国",audio_url="/static/music/xiyanghong.mp3", description="1993 年张丕基作曲，乔羽作词，央视《夕阳红》栏目主题曲，温暖舒缓。描绘晚年生活的温馨美好，曲调舒缓，传递岁月沉淀的从容与幸福。"),
            Song(title="爱的奉献", artist="韦唯", region="全国",audio_url="/static/music/aidefengxian.mp3", description="1989 年刘诗召作曲，黄奇石作词，传递爱心，成公益活动常用曲。倡导关爱他人、传递善意，旋律温暖，诠释人间大爱无疆的真谛。"),
            Song(title="好人一生平安", artist="李娜", region="全国",audio_url="/static/music/haorenyishengpingan.mp3", description="1990 年雷蕾作曲，易茗作词，电视剧《渴望》插曲，风靡全国。寄托对善良之人的美好祝愿，曲调平和，传递朴素的向善之心。"),
            Song(title="祝你平安", artist="孙悦", region="全国",audio_url="/static/music/zhunipingan.mp3", description="1994 年刘青作曲作词，旋律轻快，是经典祝福歌曲，广为流传。以真挚祝福传递温暖，旋律轻快动听，成为家喻户晓的祝福金曲。"),
            Song(title="三百六十五个祝福", artist="蔡国庆", region="全国",audio_url="/static/music/sanbailiushiwugezhufu.mp3", description="1991 年臧云飞作曲，贺东久作词，节奏明快，成节日热门曲。将每日牵挂化作祝福，节奏明快，满含真诚的美好期许。"),
            Song(title="同一首歌", artist="毛阿敏", region="全国",audio_url="/static/music/tongyishouge.mp3", description="1990 年孟卫东作曲，陈哲作词，央视《同一首歌》栏目主题曲。歌颂团结与情谊，旋律悠扬，是跨越时空的经典合唱曲目。"),
            Song(title="明天会更好", artist="罗大佑", region="台湾",audio_url="/static/music/mingtianhuigenghao.mp3", description="1985 年罗大佑等作曲，罗大佑等作词，为公益创作，凝聚正能量。传递对未来的憧憬与期盼，歌词励志，凝聚着对美好生活的向往。"),
            Song(title="北风吹", artist="朱逢博", region="河北",audio_url="/static/music/beifengchui.mp3", description="1945 年马可作曲，贺敬之等作词，歌剧《白毛女》选段，经典红色曲目。源自经典歌剧，旋律贴合剧情，唱出旧时代底层人民的生活境遇。"),
            Song(title="红星照我去战斗", artist="李双江", region="江西",audio_url="/static/music/hongxingzhaowoquzhandou.mp3", description="1973 年傅庚辰作曲，邬大为等作词，电影《闪闪的红星》插曲。展现革命少年的英勇无畏，曲调昂扬，洋溢着红色正能量。"),
            Song(title="绒花", artist="李谷一", region="全国",audio_url="/static/music/ronghua.mp3", description="1979 年王酩作曲，刘国富等作词，电影《小花》插曲，获电影金鸡奖最佳音乐。旋律柔美悠扬，歌颂无私奉献的精神，是兼具情怀与美感的经典曲目。"),
            Song(title="牡丹之歌", artist="蒋大为", region="全国",audio_url="/static/music/mudanzhige.mp3", description="1980 年吕远、唐诃作曲，乔羽作词，电影《红牡丹》主题曲，赞美牡丹。以牡丹喻美好，旋律大气磅礴，赞美生命的绚烂与坚韧。"),
            Song(title="雁南飞", artist="单秀荣", region="全国",audio_url="/static/music/yannanfei.mp3", description="1979 年李伟才作曲，李俊作词，电影《归心似箭》插曲，抒情动人。借雁南飞抒离别之情，曲调缠绵婉转，传递深沉的思念与牵挂。"),
            Song(title="驼铃", artist="蒋大为", region="全国",audio_url="/static/music/tuoling.mp3", description="1980 年王立平作曲，王立平作词，电影《戴手铐的旅客》插曲，诉战友情。饱含战友间的不舍与牵挂，旋律悠远，见证真挚的战友情谊。"),
            Song(title="知音", artist="李谷一", region="湖北",audio_url="/static/music/zhiying.mp3", description="1981 年王酩作曲，华而实作词，电影《知音》主题曲，歌颂真挚情谊。歌颂惺惺相惜的真挚情谊，曲调温婉，诠释 “知音难觅” 的珍贵。"),
            Song(title="万里长城永不倒", artist="叶振棠", region="香港",audio_url="/static/music/wanlichangchengyongbudao.mp3", description="1981 年黎小田作曲，卢国沾作词，电视剧《大侠霍元甲》主题曲。彰显民族气节与爱国情怀，节奏铿锵，激发民族自豪感。"),
            Song(title="男儿当自强", artist="林子祥", region="香港",audio_url="/static/music/nanrendangziqiang.mp3", description="1991 年黄霑作曲，黄霑作词，电影《黄飞鸿》主题曲，激昂励志。倡导坚韧不拔、奋发向上，旋律激昂，是激励男性奋进的金曲。"),
            Song(title="真心英雄", artist="周华健", region="台湾",audio_url="/static/music/zhenxinyingxiong.mp3", description="1993 年李宗盛作曲作词，周华健等演唱，传递平凡亦英雄的信念。歌颂平凡中的坚守与勇敢，歌词励志，传递 “平凡即英雄” 的信念。"),
            Song(title="中国功夫", artist="屠洪刚", region="全国",audio_url="/static/music/zhongguogongfu.mp3", description="1997 年卞留念作曲，宋小明作词，展现中国功夫魅力，气势恢宏。。"),
            Song(title="毕业歌", artist="群星", region="全国",audio_url="/static/music/biyege.mp3", description="1934 年聂耳作曲，田汉作词，电影《桃李劫》插曲，激励青年奋进。唱出青年学子的理想与担当，旋律激昂，激励年轻人奔赴新征程。"),
            Song(title="四渡赤水出奇兵", artist="中央乐团合唱团", region="贵州",audio_url="/static/music/siduchishuichuqibing.mp3", description="1975 年肖华作词，晨耕等作曲，再现红军长征智慧与勇气。再现红军长征的英勇壮举，曲调雄浑，歌颂革命先辈的智慧。"),
            Song(title="过雪山草地", artist="贾世骏", region="四川",audio_url="/static/music/guoxueshancaodi.mp3", description="1965 年肖华作词，时乐濛等作曲，刻画红军长征的艰辛与坚毅。刻画红军长征的艰辛与坚毅，旋律悲壮，传递不屈的革命精神。"),
            Song(title="大刀进行曲", artist="麦新", region="河北",audio_url="/static/music/dadaojingxingqu.mp3", description="1937 年麦新作曲作词，诞生于抗战时期，彰显抗敌决心。诞生于抗战时期，节奏铿锵，彰显中华儿女抗敌的决心与勇气。"),

            Song(title="长城谣", artist="邓丽君", region="上海", audio_url="/static/music/changcheng.mp3", description="创作于1937年抗日战争初期，由潘孑农作词，刘雪庵作曲。 这首歌原是为电影《关山万里》所作，后因战争爆发影片未能完成，但歌曲迅速传遍全国。它以苍凉悲壮的旋律，唱出了“九一八”事变后（特别是“七七事变”后）东北人民流亡关内、思念故乡的悲痛，以及全国人民同仇敌忾、抗击侵略的坚强决心。"),  
            Song(title="松花江上", artist="戴玉强", region="陕西", audio_url='/static/music/songhuajiang.mp3',description="创作于1936年，由张寒晖在陕西西安创作。他目睹了“九一八”事变后东北军民流亡关内的悲惨情景，以此歌抒发了他们对故土的思念和抗日救亡的悲愤。"),
            Song(title="嘉陵江上", artist="廖昌永", region="重庆", audio_url="/static/music/jialinjiang.mp3",description="创作于1939年抗战期间，由端木蕻良作词，贺绿汀作曲。作为“流亡三部曲”之一，此歌表达了人民在日军轰炸下，对家园破碎的悲痛和对收复失地的渴望。"),
            Song(title="游击队歌", artist="中国人民解放军总政歌舞团合唱队", region="山西", audio_url="/static/music/youjidui.mp3",description="创作于1937年底，由贺绿汀在山西临汾的八路军办事处创作。歌曲以轻快、乐观的旋律，生动展现了游击队员在敌后灵活机动、英勇抗敌的战斗形象。"),
            Song(title="在太行山上", artist="中央乐团合唱团", region="山西", audio_url="/static/music/taihangshan.mp3",description="创作于1938年，桂涛声在山西抗日根据地写下歌词，冼星海在武汉谱曲。歌曲描绘了太行山的雄伟景色，颂扬了在山中坚持抗战的军民。"),
            Song(title="延安颂", artist="李双江", region="陕西", audio_url="/static/music/yanansong.mp3",description="创作于1938年，由莫耶作词，郑律成作曲。歌曲以激昂深情的旋律，描绘了革命圣地延安的景象，表达了千万革命青年对延安的向往。"),
            Song(title="黄河颂", artist="冼星海", region="陕西", audio_url="/static/music/huanghesong.mp3",description="选自1939年在延安创作的《黄河大合唱》（光未然词，冼星海曲）。这是一首男中音独唱曲，以黄河为象征，热情讴歌了中华民族的悠久历史和坚韧不拔的斗争精神。"),
            Song(title="保卫黄河", artist="冼星海", region="陕西", audio_url="/static/music/baoweihuanghe.mp3",description="选自1939年在延安创作的《黄河大合唱》（光未然词，冼星海曲）。这是一首气势磅礴的轮唱和合唱，作为大合唱的第七乐章，发出了“保卫黄河！保卫华北！保卫全中国！”的战斗吼声。"),
            Song(title="解放区的天", artist="中央乐团合唱团", region="河北", audio_url="/static/music/jiefangqu.mp3",description="创作于1943年，由刘西林根据冀鲁边区（河北、山东一带）的民歌《十二月》调填词而成。歌曲以朴实明快的旋律，歌唱了解放区人民当家作主的喜悦心情。"),
            Song(title="太阳最红，毛主席最亲", artist="卞小贞", region="北京", audio_url="/static/music/taiyanghong.mp3",description="创作于1976年9月毛主席逝世后，由付林作词，王锡仁作曲。歌曲在北京创作，以深情的旋律表达了全国人民对毛主席的无限热爱与怀念。"),
            Song(title="春天的故事", artist="董文华", region="广东", audio_url="/static/music/chuntiandegushi.mp3",description="创作于1994年，由蒋开儒、叶旭全作词，王佑贵作曲。歌曲以广东深圳的巨大变为背景，艺术地再现了邓小平同志1992年南方谈话的场景，歌颂了改革开放的伟大决策。"),
            Song(title="红梅赞", artist="金帆合唱团", region="重庆", audio_url="/static/music/hongmeizan.mp3",description="1964年首演的歌剧《江姐》（阎肃词）的主题曲，以重庆为故事背景。歌曲借红梅不畏霜雪的品格，赞美了革命者江姐坚贞不屈、视死如归的崇高气节。"),
            Song(title="绣红旗", artist="董文华", region="重庆", audio_url="/static/music/xiuhongqi.mp3",description="歌剧《江姐》（阎肃词）中的经典唱段。歌曲以重庆渣滓洞监狱为背景，描绘了江姐等革命者在狱中得知新中国成立，怀着激动的心情绣制五星红旗的感人场面。"),
            Song(title="英雄赞歌", artist="郭兰英", region="吉林", audio_url="/static/music/yingxiongzange.mp3",description="1964年由长春电影制片厂（吉林）出品的电影《英雄儿女》插曲。歌曲（公木词，刘炽曲）以高亢激昂的旋律，赞颂了抗美援朝志愿军战士王成的英雄气概。"),
            Song(title="为了谁", artist="祖海", region="湖北/江西", audio_url="/static/music/weileshei.mp3",description="创作于1998年，（邹友开词，孟庆云曲），是为当年长江流域（特别是湖北、江西等地）抗洪抢险的解放军战士而作，歌颂了他们不畏牺牲、保卫人民的奉献精神。"),
            Song(title="走进新时代", artist="张也", region="北京", audio_url="/static/music/zoujinxinshidai.mp3",description="创作于1997年，由蒋开儒作词，印青作曲，在北京首演。作为迎接中共十五大和香港回归的献礼作品，歌曲歌颂了改革开放和社会主义现代化建设的新篇章。"),
            Song(title="让我们荡起双桨", artist="蓝天合唱团", region="北京", audio_url="/static/music/rangwomendangqi.mp3",description="1955年电影《祖国的花朵》插曲，由乔羽作词，刘炽作曲。歌曲描绘了少先队员在北京北海公园泛舟歌唱的情景，旋律优美，充满了新中国儿童的幸福感。"),
            Song(title="沂蒙颂", artist="张也", region="山东", audio_url="/static/music/yimengsong.mp3",description="1972年芭蕾舞剧《沂蒙颂》的主题曲。该剧以山东沂蒙山革命根据地为背景，乐曲（刘廷禹等作曲）吸取了当地民歌元素，颂扬了军民鱼水情。"),
            Song(title="弹起我心爱的土琵琶", artist="阎维文", region="山东", audio_url="/static/music/tupipa.mp3",description="1956年电影《铁道游击队》插曲，（芦芒、何彬词，吕其明曲）。歌曲以山东微山湖为背景，表现了抗日游击队员在艰苦环境中的革命乐观主义精神。"),
            Song(title="山丹丹花开红艳艳", artist="阿宝", region="陕西", audio_url="/static/music/shandandanhuakai.mp3",description="创作于1971年，（李若然等词，刘烽曲）。歌曲以陕北民歌为基础，用山丹丹花比喻革命，热情歌颂了中央红军长征到达陕北的重大历史事件。"),
            Song(title="人说山西好风光", artist="郭兰英", region="山西", audio_url="/static/music/shanxihaofengguang.mp3", description="1959年电影《我们村里的年轻人》插曲（乔羽词，张棣昌曲）。歌曲以优美抒情的旋律，描绘了山西的壮丽山河与人民建设家乡的蓬勃热情。"),
            Song(title="映山红", artist="宋祖英", region="江西", audio_url="/static/music/yingshanhong.mp3",description="1974年电影《闪闪的红星》插曲，（陆柱国词，傅庚辰曲）。歌曲以江西革命根据地为背景，通过孩子对红军的期盼，表达了人民对红军的热爱和对光明的向往。"),
            Song(title="我们新疆好地方", artist="新疆军区文工团", region="新疆", audio_url="/static/music/womenxinjiang.mp3",description="创作于1951年（马寒冰词，刘炽曲）。歌曲旋律欢快，富有新疆民歌特色，展现了新疆解放后各族人民团结一心，建设美好家园的壮丽画卷。"),
            Song(title="十送红军", artist="宋祖英", region="江西", audio_url="/static/music/shisonghongjun.mp3",description="源自江西赣南的客家民歌《送郎歌》，后在60年代被改编加工（张士燮等整理）。歌曲通过“十送”的细节，真切表现了红军长征前，根据地人民与红军依依惜别的军民鱼水深情。"),
            Song(title="送战友", artist="李双江", region="吉林", audio_url="/static/music/songzhanyou.mp3",description="1974年长春电影制片厂（吉林）电影《侦察兵》插曲（王振词，臧东升曲）。歌曲旋律深情舒缓，表达了革命战友间告别时的真挚情谊。"),
            Song(title="在希望的田野上", artist="张也", region="北京", audio_url="/static/music/zaixiwangdeyuanye.mp3",description="创作于1982年（陈晓光词，施光南曲）。歌曲在北京创作，以昂扬的旋律和生动的歌词，描绘了十一届三中全会后中国农村改革带来的勃勃生机。"),
            Song(title="祝酒歌", artist="降央卓玛", region="北京", audio_url="/static/music/zhujiuge.mp3",description="创作于1976年10月（韩伟词，施光南曲）。这首歌是为庆祝粉碎“四人帮”而作，在北京首演，表达了全国人民对“第二次解放”的喜悦和对未来的美好祝愿。"),
            Song(title="山歌好比春江水", artist="斯琴格日乐", region="广西", audio_url="/static/music/shangehaobi.mp3",description="1960年电影《刘三姐》插曲（乔羽词），根据广西壮族民歌改编。歌曲是“歌仙”刘三姐的经典对歌唱段，旋律优美灵动，展现了广西的山水之美和民歌文化。"),
            Song(title="翻身农奴把歌唱", artist="才旦卓玛", region="西藏", audio_url="/static/music/fanshennongnu.mp3",description="1965年纪录片《今日西藏》的主题曲（李堃词，阎飞曲）。由藏族歌唱家才旦卓玛演唱，以真挚的感情和藏族音乐风格，歌颂了西藏民主改革后，翻身农奴的幸福生活。"),
            Song(title="军民大生产", artist="群星", region="甘肃", audio_url="/static/music/junmindashengchan.mp3", description="诞生于甘肃陇东的革命民歌，生动再现了当年边区军民热火朝天开展大生产运动的历史场景。"),
            Song(title="浙一抹中国红", artist="群星", region="浙江", audio_url="/static/music/zheyimozhongguohong.mp3", description="歌颂浙江革命志士的新时代红歌，以深情的旋律致敬为解放事业献身的英烈。"),
            Song(title="娘子军连歌", artist="群星", region="海南", audio_url="/static/music/niangzijunliange.mp3", description="电影《红色娘子军》主题曲，铿锵有力地唱出了海南女子革命部队的英勇斗志和集体精神。"),
            Song(title="万泉河水清又清", artist="黑鸭子演唱组", region="海南", audio_url="/static/music/wanquanheshuiqingyouqing.mp3", description="芭蕾舞剧《红色娘子军》的经典插曲，以悠扬动人的旋律展现了海南革命根据地军民之间的鱼水深情。"),
            Song(title="绣金匾", artist="群星", region="甘肃", audio_url="/static/music/xiujinbian.mp3", description="陇东红色歌曲，内容为歌颂中国共产党、伟大领袖毛主席、人民军队等。"),
            Song(title="咱们的领袖毛泽东", artist="群星", region="甘肃", audio_url="/static/music/zanmendelingxiumaozedong.mp3", description="源自陇东的革命民歌，歌颂了领袖与人民的深厚情感。"),
            Song(title="渔光曲", artist="彭丽媛", region="上海", audio_url="/static/music/yuguangqu.mp3", description="中国早期左翼电影音乐的标杆，它首次将底层劳动人民的苦难通过音乐具象化，后续《大路歌》《毕业歌》《义勇军进行曲》等优秀电影歌曲的创作均受其启发。"),
            Song(title="抗敌歌", artist="中国广播艺术团", region="上海", audio_url="/static/music/kangdige.mp3", description="1931 年 “九一八” 事变后由黄自作曲、韦瀚章作词的抗日救亡歌曲，以混声四部合唱形式号召民众团结御侮、共赴国难，饱含强烈爱国激情，是中国早期抗日救亡音乐的重要代表作品。"),
            Song(title="红旗颂", artist="中国人民解放军军乐团", region="上海", audio_url="/static/music/hongqisong.mp3", description="《红旗颂》是 1965 年由吕其明为纪念中国共产党成立 40 周年创作的交响诗，歌颂红旗所承载的革命历程、民族精神与时代力量，是中国交响音乐的经典代表作。"),
            Song(title="八月桂花遍地开", artist="群星", region="河南", audio_url="/static/music/bayueguihuabiandikai.mp3", description="源自河南商城的革命艺人根据当地民歌《八段锦》改编而成，并唱响全国。"),
            Song(title="大会师", artist="罗龙", region="广西",audio_url="/static/music/dahuishi.mp3", description="1936 年创作，纪念红军三大主力会师，彰显革命胜利的喜悦与团结力量。"),
            Song(title="广西红", artist="周彬", region="广西",audio_url="/static/music/guangxihong.mp3", description="20 世纪 90 年代创作，歌颂广西红色历史与民族精神，旋律激昂奋进。"),
            Song(title="壮锦送给毛主席", artist="八只眼", region="广西",audio_url="/static/music/zhuangjinsonggeimaozhuxi.mp3", description="1959 年创作，以壮锦为载体，抒发壮族人民对领袖的爱戴与感恩。"),        
            Song(title="我爱五指山,我爱万泉河", artist="李双江", region="海南",audio_url="/static/music/woaiwuzhishanwoaiwanquanhe.mp3", description="1973 年创作，赞美海南秀丽风光，抒发对革命圣地的热爱。"),
            Song(title="娘子军连歌", artist="群星", region="海南",audio_url="/static/music/niangzijunliange.mp3", description="1961 年创作，源自电影《红色娘子军》，展现女战士的英勇无畏与革命信念。"),
            Song(title="万泉河水清又清", artist="童丽", region="海南",audio_url="/static/music/wanquanheshuiqingyouqing.mp3", description="1961 年创作，电影《红色娘子军》插曲，歌颂军民鱼水深情与革命情怀。"),
            Song(title="大美青海", artist="琼雪卓玛&次仁桑珠", region="青海",audio_url="/static/music/dameiqinhai.mp3", description="2010 年前后创作，描绘青海壮美景色，传递对家乡的热爱与自豪。"),
            Song(title="厚土", artist="袁怀湘", region="河南",audio_url="/static/music/houtu.mp3", description="20 世纪 80 年代创作，扎根河南乡土文化，歌颂土地的孕育之恩与人民的质朴。"),
            Song(title="送郎当红军", artist="中央乐团合唱团", region="河南",audio_url="/static/music/songlangdanghongjun.mp3", description="1934 年创作，反映河南妇女支持亲人参军的家国情怀与革命大义。"),
            Song(title="韩彦红色圣地", artist="史宁广", region="河南",audio_url="/static/music/hanyanhongseshengdi.mp3", description="21 世纪初创作，缅怀韩彦革命历史，传承红色基因与奋斗精神。"),
            Song(title="游击队之歌", artist="野孩子", region="湖南",audio_url="/static/music/youjiduizhige.mp3", description="1937 年创作，展现湖南游击队的机智勇敢，传递抗敌必胜的信念。"),
            Song(title="浏阳河", artist="李谷一", region="湖南",audio_url="/static/music/liuyanghe.mp3", description="1951 年创作，借浏阳河抒发对领袖的敬仰，旋律轻快洋溢乡土气息。"),
            Song(title="挑担茶叶上北京", artist="何纪光", region="湖南",audio_url="/static/music/tiaodanchayeshangbeijin.mp3", description="1960 年创作，展现湖南茶农的淳朴热情，传递对首都的向往。"),
            Song(title="我爱韶山的红杜鹃", artist="张映龙", region="湖南",audio_url="/static/music/woaishaoshandehongdujuan.mp3", description="1976 年创作，缅怀毛主席，歌颂韶山红色历史与革命精神。"),
        ]
        db.session.bulk_save_objects(songs_to_add)

    # 填充文章（微课）数据 - 新增示例视频链接
    if not Article.query.first():
        articles_to_add = [
            Article(
                title="《从南湖红船到民族曙光：初心为何照亮百年》", 
                summary="《国际歌（中文版）》是瞿秋白填词、源自法国工人斗争的经典红色歌曲，其首个中文全译本诞生于1923年，用于传播共产主义理想，鼓舞无产阶级革命斗志。20世纪初，马克思主义思想传入中国，迫切需要一首能凝聚工农、阐发理想的战歌。革命先驱瞿秋白在《新青年》上发表其译配的《国际歌》，并创造性音译“英特纳雄耐尔”一词，旨在让中国劳动者与全世界无产者同声相应。歌曲随革命洪流传唱，从安源路矿到长征路途，成为信念的号角。它反映了早期共产主义者追求真理、团结奋斗的精神，被视作中国共产党的精神象征之一。其旋律磅礴 universal，歌词充满召唤力，成为红色经典，激励后人不忘阶级初心、继承国际主义精神。",
                video_url="static/videos/1_guojige.mp4" # 示例视频
            ),
            Article(
                title="《井冈山上的火种：星星之火如何燎原》", 
                summary="《三大纪律八项注意》是程坦编词、集体谱曲的经典革命歌曲，诞生于中国工农红军长征时期的革命实践。1935年，为巩固部队纪律、密切军民关系，中国共产党在革命军队中推行纪律规范建设，毛泽东亲自制定了\"三大纪律、六项注意\"的基本要求，后发展为\"三大纪律、八项注意\"。这首歌曲以通俗易懂的歌词、铿锵有力的旋律，将革命军队的纪律要求编成朗朗上口的军歌，在红军各部队中广泛传唱。歌曲深刻体现了人民军队的本质特征，展现了中国共产党领导下革命军队严明的纪律作风和深厚的军民鱼水情，成为我军政治工作的重要载体。其鲜明的节奏和朴实的歌词，使其在革命战争年代发挥了重要的宣传教育作用，至今仍是传承红色基因、弘扬革命传统的重要经典。",
                video_url="static/videos/2_sandajilvbaxiangzhuyi.mp4"
            ),
            Article(
                title="《两万五千里的信仰：长征为何震撼世界》", 
                summary="《十送红军》是张士燮作词、朱正本作曲的经典红色民歌。创作于1960年，取材于中央红军长征出发时苏区群众送别红军的感人场景。歌曲以赣南采茶戏为基础音乐素材，通过\"一送里格红军\"等十段歌词，细腻刻画了苏区人民与红军战士的深厚情谊。旋律优美动人，歌词真挚朴实，既展现了革命战争时期军民一家的动人情景，也体现了人民群众对革命事业的坚定支持。该作品被誉为\"红色经典民歌\"，至今仍在各地广泛传唱。",
                video_url="static/videos/3_shisonghongjun.mp4"
            ),
            Article(
                title="《一个民族的觉醒：抗战精神从何而来》", 
                summary="《义勇军进行曲》是田汉作词、聂耳作曲的中华民族抗战歌曲。创作于1935年民族危亡之际，最初作为电影《风云儿女》主题曲问世。歌曲以激昂的旋律和铿锵的歌词，发出\"中华民族到了最危险的时候\"的呐喊，唤醒了全国人民的抗战意识。1949年被选定为中华人民共和国代国歌，1982年正式确定为国歌。这首歌凝聚了中华民族不屈不挠的民族精神，展现了中国人民捍卫国家尊严的坚定意志，成为激励一代代中国人奋勇前进的精神力量。",
                video_url="static/videos/4_yiyongjunjinxingqu.mp4"
            ),
            Article(
                title="《从硝烟到新中国：人民解放军何以赢得胜利》", 
                summary="《没有共产党就没有新中国》是曹火星词曲创作的经典红色歌曲。创作于1943年抗日战争时期，歌曲以朴实的语言、明快的旋律，阐述了\"没有共产党就没有新中国\"这一历史真理。歌词通过排比句式，历数共产党坚持抗战、改善民生、建设根据地等功绩，旋律汲取了民间音乐的养分，易于传唱。这首歌在解放区迅速流传，成为人民群众歌颂共产党、歌颂新中国的代表作品，至今仍是传承红色基因的重要载体。",
                video_url="static/videos/5_meiyougonchandangjiumeiyouxinzhongguo.mp4" # 示例视频
            ),
            Article(
                title="《开国大典：礼炮为何震动中国人的灵魂》", 
                summary="《歌唱祖国》是王莘词曲创作的经典爱国主义歌曲。创作于1950年新中国成立初期，歌曲以豪迈的旋律、真挚的情感，抒发了对新生祖国的热爱之情。\"五星红旗迎风飘扬，胜利歌声多么响亮\"等歌词，生动展现了站起来的中国人民的自豪与喜悦。这首歌因其磅礴大气的音乐风格和深切感人的爱国情怀，被誉为\"第二国歌\"，在各类重大庆典和外交场合奏响，成为展现国家形象、凝聚民族力量的重要音乐作品。",
                video_url="static/videos/6_gechangzuguo.mp4"
            ),
            Article(
                title="《从一穷二白到全民奋进：社会主义改造的力量》", 
                summary="《《社会主义好》是希扬作词、李焕之作曲的社会主义建设歌曲。创作于1957年社会主义改造时期，歌曲以激昂的旋律、坚定的歌词，歌颂了社会主义制度的优越性。歌词中\"社会主义好，社会主义好，社会主义国家人民地位高\"等词句，表达了人民群众对社会主义道路的坚定信念。这首歌在社会主义建设高潮时期广泛传唱，成为那个激情燃烧岁月的重要音乐记忆，展现了中国人民建设社会主义的豪情壮志。",
                video_url="static/videos/7_shehuizhuyihao.mp4"
            ),
          Article(
                title="《春天的决策：为什么说1978改变了中国？》", 
                summary="《《春天的故事》是蒋开儒、叶旭全作词，王佑贵作曲的改革开放颂歌。创作于1994年，歌曲以诗意的语言、优美的旋律，讲述了改革开放以来中国发生的巨大变化。\"1979年，那是一个春天，有一位老人在中国的南海边画了一个圈\"等歌词，生动记录了改革开放的历史进程。这首歌深情歌颂了改革开放的伟大决策，展现了中国特色社会主义道路的蓬勃生机，成为改革开放时代的音乐见证。",
                video_url="static/videos/8_chuntiandegushi.mp4"
            ),
            Article(
                title="《跨越百年的回家路：香港澳门回归背后的力量》", 
                summary="《七子之歌・澳门》是闻一多作词、李海鹰作曲的澳门回归主题歌曲。创作于1999年澳门回归之际，歌词取自闻一多1925年创作的《七子之歌》组诗。歌曲以童声演唱为主，\"你可知Macau不是我真姓\"等歌词，抒发了澳门游子对祖国的深切思念。这首歌在澳门回归庆典上感动了无数中华儿女，成为庆祝澳门回归、表达民族情感的经典作品，展现了中华民族实现祖国统一的坚定信念。",
                video_url="static/videos/9_qizizhige.mp4" # 示例视频
            ),
            Article(
                title="《全面小康的答案：14亿人共同写下的奇迹》", 
                summary="《脱贫宣言》是新时代脱贫攻坚主题歌曲。创作于脱贫攻坚战决胜时期，歌曲以铿锵的旋律、坚定的歌词，展现了中国共产党带领人民消除绝对贫困的宏伟实践。歌词生动描绘了脱贫攻坚的壮阔图景，歌颂了扶贫干部的奉献精神和脱贫群众的奋斗历程。这首歌凝聚了全国人民同心协力、战胜贫困的坚定意志，记录了人类减贫史上的中国奇迹，成为新时代奋斗精神的音乐写照。",
                video_url="static/videos/10_tuopinxuanyan.mp4"
            ),
            Article(
                title="《百年红船到巨轮：中国共产党为什么能？》", 
                summary="《不忘初心》是朱海作词、舒楠作曲的新时代主旋律歌曲。创作于2017年，歌曲以深情的旋律、真挚的歌词，诠释了中国共产党人的初心和使命。\"万水千山不忘来时路\"等歌词，深刻表达了共产党人牢记宗旨、继续前进的坚定信念。这首歌在党的十九大期间广泛传唱，成为开展\"不忘初心、牢记使命\"主题教育的重要载体，展现了新时代中国共产党人坚守初心、担当使命的精神风貌。",
                video_url="static/videos/11_buwangchuxin.mp4"
            ),
          Article(
                title="《强国之路：中华民族复兴为何“势不可挡”》", 
                summary="《我们都是追梦人》是新时代青春励志歌曲。创作于2019年，歌曲以动感的节奏、励志的歌词，展现了新时代中国人民特别是青年一代追逐梦想、奋发向上的精神风貌。\"千山万水奔向天地跑道，你追我赶起航汹涌春潮\"等歌词，生动描绘了亿万人民同心共筑中国梦的壮丽画卷。这首歌洋溢着青春激情，充满着时代气息，成为激励新时代奋斗者勇敢追梦的青春战歌。",
                video_url="static/videos/12_womendoushizhuimengren.mp4"
            ),

        ]
        db.session.bulk_save_objects(articles_to_add)
    
    # 填充历史事件数据
    if not HistoricalEvent.query.first():
        events_to_add = [
            HistoricalEvent(year=1911, event_description="辛亥革命爆发，结束了中国两千多年的封建帝制。", detailed_description="由孙中山领导，旨在推翻清朝专制帝制、建立共和政体的全国性革命。武昌起义是其开端，最终促使清帝退位，中华民国成立。"),
            HistoricalEvent(year=1919, event_description="五四运动爆发，标志着中国新民主主义革命的开端。", detailed_description="一场以青年学生为主，广大群众、市民、工商人士等阶层共同参与的爱国运动，是中国人民彻底的反对帝国主义、封建主义的爱国运动。"),
            HistoricalEvent(year=1921, event_description="中国共产党第一次全国代表大会在上海召开，宣告中国共产党成立。", detailed_description="大会确定党的名称为“中国共产党”，通过了党的第一个纲领，选举产生了党的中央领导机构，宣告了中国共产党的正式诞生。"),
            HistoricalEvent(year=1927, event_description="南昌起义，打响了武装反抗国民党反动派的第一枪。", detailed_description="由周恩来、贺龙等人领导的起义，标志着中国共产党独立领导革命战争、创建人民军队和武装夺取政权的开始。"),
            HistoricalEvent(year=1931, event_description="九一八事变，日本开始侵华战争。这一时期诞生了著名红歌《松花江上》。", detailed_description="日本在中国东北蓄意制造并发动的一场侵华战争，是日本帝国主义侵华的开端。《松花江上》由张寒晖创作，唱出了东北人民流离失所、家破人亡的悲痛。"),
            HistoricalEvent(year=1934, event_description="中央红军开始长征，谱写了中国革命史的光辉篇章。", detailed_description="红一方面军主力被迫撤离中央革命根据地，进行战略转移。长征历时两年，行程二万五千里，是中国革命史上的伟大奇迹。"),
            HistoricalEvent(year=1935, event_description="遵义会议召开。同年，《义勇军进行曲》诞生，极大地鼓舞了抗日士气。", detailed_description="遵义会议确立了毛泽东在党和红军中的领导地位。同年，由田汉作词、聂耳作曲的《义勇军进行曲》成为抗日救亡的号角。"),
            HistoricalEvent(year=1937, event_description="七七事变（卢沟桥事变），标志着全国性抗日战争的开始。这一时期诞生了《大刀进行曲》、《游击队歌》等。"),
            HistoricalEvent(year=1939, event_description="冼星海创作《黄河大合唱》，其中的《保卫黄河》成为抗日救亡的时代强音。", detailed_description="在延安创作的这部大型合唱作品，以黄河为背景，热情歌颂了中华民族的源远流长的光荣历史和中国人民坚强不屈的斗争精神。"),
            HistoricalEvent(year=1943, event_description="歌曲《没有共产党就没有新中国》创作完成，在各解放区广为传唱。", detailed_description="由曹火星创作，以朴实的语言、流畅的旋律，道出了中国人民的心声，成为一首家喻户晓的革命歌曲。"),
            HistoricalEvent(year=1945, event_description="抗日战争胜利。源自陕北的民歌《东方红》经过改编后，开始在解放区流行。", detailed_description="中国人民经过14年艰苦卓绝的斗争，取得了抗日战争的伟大胜利。在延安，农民歌手李有源将陕北民歌重新填词，创作出《东方红》。"),
            HistoricalEvent(year=1949, event_description="中华人民共和国成立，开辟了中国历史的新纪元。", detailed_description="10月1日，毛泽东主席在北京天安门城楼上向全世界庄严宣告中华人民共和国中央人民政府成立，中国历史从此进入了一个新的纪元。"),
            HistoricalEvent(year=1950, event_description="抗美援朝战争爆发。这一时期诞生了《中国人民志愿军战歌》。", detailed_description="中国人民志愿军赴朝作战，保家卫国。“雄赳赳，气昂昂，跨过鸭绿江”的歌声响彻云霄，展现了志愿军的英雄气概。"),
            HistoricalEvent(year=1951, event_description="《歌唱祖国》由王莘在天安门广场上获得灵感后创作，迅速传遍全国。", detailed_description="歌曲以其雄壮豪迈的旋律和振奋人心的歌词，成为新中国最具代表性的颂歌之一，被誉为“第二国歌”。"),
            HistoricalEvent(year=1956, event_description="电影《上甘岭》上映，插曲《我的祖国》成为经典。", detailed_description="影片讲述了上甘岭战役的残酷与志愿军的英勇。插曲《我的祖国》由郭兰英演唱，前半部分温婉抒情，后半部分激昂雄壮，成为传世经典。"),
            HistoricalEvent(year=1964, event_description="我国第一颗原子弹爆炸成功，极大地提升了国防实力和国际地位。", detailed_description="这一成就标志着中国成为世界上第五个拥有核武器的国家，对于维护国家安全、打破核垄断具有重大战略意义。"),
            HistoricalEvent(year=1970, event_description="我国第一颗人造地球卫星“东方红一号”发射成功。", detailed_description="卫星成功进入预定轨道，并播送《东方红》乐曲，标志着中国进入了航天时代。"),
            HistoricalEvent(year=1978, event_description="党的十一届三中全会召开，作出改革开放的重大决策。", detailed_description="会议重新确立了马克思主义的思想路线、政治路线和组织路线，实现了新中国成立以来党的历史上具有深远意义的伟大转折。"),
            HistoricalEvent(year=1979, event_description="歌曲《春天的故事》歌颂了改革开放的总设计师和深圳经济特区的建立。", detailed_description="歌曲以抒情的旋律，描绘了邓小平同志在中国南海边画了一个圈，开启了改革开放的伟大历程。它不仅是对一位伟人的颂歌，更是对一个伟大时代的赞美。"),
            HistoricalEvent(year=1984, event_description="歌曲《我的中国心》由香港歌手张明敏在春晚演唱，引起巨大共鸣。", detailed_description="在改革开放初期，这首歌以其真挚的情感和朴素的歌词，唱出了海内外华人对祖国的深厚感情，迅速传遍大江南北。"),
            HistoricalEvent(year=1997, event_description="香港回归祖国。《东方之珠》成为庆祝香港回归的代表性歌曲。", detailed_description="中国政府恢复对香港行使主权，中华人民共和国香港特别行政区成立。罗大佑创作的《东方之珠》以其优美的旋律，表达了对香港未来的美好祝愿。"),
            HistoricalEvent(year=1999, event_description="澳门回归祖国。歌曲《七子之歌》广为传唱，表达了澳门同胞的回归心声。", detailed_description="中国政府恢复对澳门行使主权。闻一多先生的诗作《七子之歌·澳门》被谱上曲，成为迎接澳门回归的标志性歌曲。"),
        ]
        db.session.bulk_save_objects(events_to_add)

    db.session.commit()

    # 填充竞答题目数据
    if not QuizQuestion.query.first():
        questions_to_add = [
            # 简单题目（10分）
            QuizQuestion(
                question="《中华人民共和国国歌》的原名是什么？",
                option_a="《东方红》",
                option_b="《义勇军进行曲》",
                option_c="《没有共产党就没有新中国》",
                option_d="《歌唱祖国》",
                correct_answer="B",
                explanation="《中华人民共和国国歌》原名为《义勇军进行曲》，创作于1935年。",
                difficulty="easy",
                points=10
            ),
            QuizQuestion(
                question="《东方红》这首歌来源于哪个地区的民歌？",
                option_a="陕北",
                option_b="东北",
                option_c="江南",
                option_d="西南",
                correct_answer="A",
                explanation="《东方红》源自陕北的革命民歌，歌颂了毛泽东同志和人民的深厚感情。",
                difficulty="easy",
                points=10
            ),
            QuizQuestion(
                question="《没有共产党就没有新中国》这首歌创作于哪一年？",
                option_a="1938年",
                option_b="1943年",
                option_c="1949年",
                option_d="1952年",
                correct_answer="B",
                explanation="《没有共产党就没有新中国》创作于1943年抗日战争时期。",
                difficulty="easy",
                points=10
            ),
            QuizQuestion(
                question="《歌唱祖国》被誉为什么？",
                option_a="第三国歌",
                option_b="第二国歌",
                option_c="军歌",
                option_d="民歌",
                correct_answer="B",
                explanation="《歌唱祖国》创作于1951年，被誉为\"第二国歌\"。",
                difficulty="easy",
                points=10
            ),
            QuizQuestion(
                question="《我和我的祖国》的首唱者是哪位歌手？",
                option_a="邓丽君",
                option_b="李谷一",
                option_c="彭丽媛",
                option_d="宋祖英",
                correct_answer="B",
                explanation="《我和我的祖国》由张藜作词、秦咏诚作曲，李谷一于1985年首唱。",
                difficulty="easy",
                points=10
            ),
            
            # 中等题目（20分）
            QuizQuestion(
                question="《黄河大合唱》的词作者是谁？",
                option_a="田汉",
                option_b="光未然",
                option_c="聂耳",
                option_d="冼星海",
                correct_answer="B",
                explanation="《黄河大合唱》由光未然作词、冼星海作曲，1939年在延安创作完成。",
                difficulty="medium",
                points=20
            ),
            QuizQuestion(
                question="《洪湖水，浪打浪》是哪部歌剧中的经典唱段？",
                option_a="《白毛女》",
                option_b="《洪湖赤卫队》",
                option_c="《江姐》",
                option_d="《刘胡兰》",
                correct_answer="B",
                explanation="《洪湖水，浪打浪》是歌剧《洪湖赤卫队》的选曲，描绘了湖北洪湖地区的风光。",
                difficulty="medium",
                points=20
            ),
            QuizQuestion(
                question="《南泥湾》歌颂的什么精神？",
                option_a="革命斗争精神",
                option_b="自力更生、艰苦奋斗",
                option_c="团结友爱",
                option_d="无私奉献",
                correct_answer="B",
                explanation="《南泥湾》诞生于抗战时期，歌颂了八路军三五九旅在南泥湾垦荒屯田、自力更生的奋斗精神。",
                difficulty="medium",
                points=20
            ),
            QuizQuestion(
                question="《义勇军进行曲》最初是哪部电影的插曲？",
                option_a="《风云儿女》",
                option_b="《桃李劫》",
                option_c="《大路》",
                option_d="《马路天使》",
                correct_answer="A",
                explanation="《义勇军进行曲》最初是1935年电影《风云儿女》的主题曲。",
                difficulty="medium",
                points=20
            ),
            QuizQuestion(
                question="《游击队歌》的作者是谁？",
                option_a="聂耳",
                option_b="贺绿汀",
                option_c="冼星海",
                option_d="吕骥",
                correct_answer="B",
                explanation="《游击队歌》由贺绿汀于1937年在山西创作，生动展现了游击队员的战斗形象。",
                difficulty="medium",
                points=20
            ),
            
            # 困难题目（30分）
            QuizQuestion(
                question="《毕业歌》是哪部电影的插曲？这部电影的导演是谁？",
                option_a="《马路天使》，袁牧之",
                option_b="《桃李劫》，应云卫",
                option_c="《风云儿女》，许幸之",
                option_d="《都市风光》，袁牧之",
                correct_answer="B",
                explanation="《毕业歌》是1934年电影《桃李劫》的插曲，由聂耳作曲、田汉作词，应云卫导演。",
                difficulty="hard",
                points=30
            ),
            QuizQuestion(
                question="《在那遥远的地方》这首歌的灵感源自哪里？",
                option_a="内蒙古草原",
                option_b="青海金银滩草原",
                option_c="新疆天山",
                option_d="西藏高原",
                correct_answer="B",
                explanation="《在那遥远的地方》是王洛宾1939年赴青海金银滩草原采风时，受藏族姑娘卓玛的灵感启发创作的。",
                difficulty="hard",
                points=30
            ),
            QuizQuestion(
                question="《松花江上》的创作者是谁？他在创作这首歌时的背景是什么？",
                option_a="聂耳，1935年上海",
                option_b="张寒晖，1936年西安目睹东北军民流亡",
                option_c="贺绿汀，1937年山西抗日前线",
                option_d="冼星海，1938年延安",
                correct_answer="B",
                explanation="《松花江上》由张寒晖1936年在陕西西安创作，他目睹了\"九一八\"事变后东北军民流亡关内的悲惨情景。",
                difficulty="hard",
                points=30
            ),
            QuizQuestion(
                question="《红星照我去战斗》是哪部电影的主题曲？这部电影讲述了什么故事？",
                option_a="《闪闪的红星》，讲述了少年潘冬子在革命斗争中成长的故事",
                option_b="《智取威虎山》，讲述了杨子荣智斗土匪的故事",
                option_c="《红色娘子军》，讲述了海南女战士的革命故事",
                option_d="《白毛女》，讲述了农民反抗地主压迫的故事",
                correct_answer="A",
                explanation="《红星照我去战斗》是1973年电影《闪闪的红星》的插曲，讲述了少年潘冬子在革命斗争中成长的故事。",
                difficulty="hard",
                points=30
            ),
            QuizQuestion(
                question="《十送红军》源自哪里？经过怎样的改编历程？",
                option_a="湖南民歌，1970年代改编",
                option_b="江西赣南客家民歌《送郎歌》，1960年代改编加工",
                option_c="四川民歌，1980年代改编",
                option_d="陕北民歌，1950年代改编",
                correct_answer="B",
                explanation="《十送红军》源自江西赣南的客家民歌《送郎歌》，后在60年代被张士燮等改编加工，通过\"十送\"的细节，真切表现了红军长征前根据地人民与红军的深情。",
                difficulty="hard",
                points=30
            ),
            QuizQuestion(
                question="《义勇军进行曲》被正式确定为中华人民共和国国歌是在哪一年？",
                option_a="1949年",
                option_b="1982年",
                option_c="2004年",
                option_d="1950年",
                correct_answer="B",
                explanation="1949年《义勇军进行曲》被选定为中华人民共和国代国歌，1982年被全国人民代表大会正式确认为国歌。",
                difficulty="hard",
                points=30
            ),
            QuizQuestion(
                question="《黄河大合唱》包含几个乐章？其中最著名的乐章是哪个？",
                option_a="6个乐章，《黄水谣》",
                option_b="7个乐章，《保卫黄河》",
                option_c="8个乐章，《黄河颂》",
                option_d="9个乐章，《怒吼吧，黄河》",
                correct_answer="B",
                explanation="《黄河大合唱》包含9个乐章（不是7个），其中《保卫黄河》是最著名和广泛传播的乐章。",
                difficulty="hard",
                points=30
            ),
            QuizQuestion(
                question="《春天的故事》歌词中\"1979年，那是一个春天\"指的是什么历史事件？",
                option_a="改革开放拉开序幕",
                option_b="邓小平南方谈话",
                option_c="深圳经济特区建立",
                option_d="党的十一届三中全会召开",
                correct_answer="A",
                explanation="《春天的故事》中\"1979年，那是一个春天\"指的是改革开放拉开序幕，\"1992年又是一个春天\"指的是邓小平南方谈话。",
                difficulty="hard",
                points=30
            ),
            QuizQuestion(
                question="《七子之歌·澳门》的歌词源自谁的诗作？这首歌诞生于什么时候？",
                option_a="郭沫若，1919年五·四运动时期",
                option_b="闻一多1925年创作的《七子之歌》组诗，1999年澳门回归时谱曲",
                option_c="艾青，1940年抗战时期",
                option_d="臧克家，1970年代",
                correct_answer="B",
                explanation="《七子之歌·澳门》歌词取自闻一多1925年创作的《七子之歌》组诗，1999年澳门回归时经李海鹰谱曲广为传唱。",
                difficulty="hard",
                points=30
            )
        ]
        db.session.bulk_save_objects(questions_to_add)
        print("已初始化竞答题目数据。")

    # 填充成就徽章数据 - 支持增量添加（不删除现有成就）
    # 获取现有成就名称集合，避免重复添加
    existing_achievement_names = set(ach.name for ach in Achievement.query.all())
    
    # 定义所有成就
    all_achievements = [
        # 答题类成就
        Achievement(
            name="初学乍练",
            description="答对第1道题目，开始你的红歌知识之旅！",
            icon="🎯",
            category="quiz",
            condition_type="quiz_correct",
            condition_value=1,
            points=10
        ),
        Achievement(
            name="渐入佳境",
            description="答对10道题目，你对红歌已经越来越熟悉了！",
            icon="🎯",
            category="quiz",
            condition_type="quiz_correct",
            condition_value=10,
            points=30
        ),
        Achievement(
            name="红歌专家",
            description="答对50道题目，你已经是一位红歌知识专家了！",
            icon="🎯",
            category="quiz",
            condition_type="quiz_correct",
            condition_value=50,
            points=100
        ),
        
        # 浏览类成就
        Achievement(
            name="初识峥嵘",
            description="浏览第1篇AI红歌微课，开启学习之旅！",
            icon="📖",
            category="learn",
            condition_type="learn_articles",
            condition_value=1,
            points=30
        ),
        Achievement(
            name="博学多才",
            description="浏览10篇AI红歌微课，你已经了解了不少历史故事！",
            icon="📚",
            category="learn",
            condition_type="learn_articles",
            condition_value=10,
            points=100
        ),
        
        # 收藏类成就
        Achievement(
            name="初露锋芒",
            description="收藏1首红歌，开启你的音乐收藏之旅！",
            icon="🎵",
            category="song",
            condition_type="favorite_songs",
            condition_value=1,
            points=30
        ),
        Achievement(
            name="收藏家",
            description="收藏10首红歌，你的音乐库已经相当丰富了！",
            icon="🎵",
            category="song",
            condition_type="favorite_songs",
            condition_value=10,
            points=100
        ),
        
        # 创作类成就
        Achievement(
            name="初试锋芒",
            description="创作第1首红歌，开启你的创作之旅！",
            icon="🎨",
            category="create",
            condition_type="create_songs",
            condition_value=1,
            points=50
        ),
        Achievement(
            name="创作达人",
            description="创作5首红歌，你的创作能力已经很出色了！",
            icon="🎵",
            category="create",
            condition_type="create_songs",
            condition_value=5,
            points=150
        ),
        
        # 对话类成就
        Achievement(
            name="初探古今",
            description="与红歌专家进行第1次对话，开始探索红歌背后的故事！",
            icon="💬",
            category="chat",
            condition_type="chat_messages",
            condition_value=1,
            points=30
        ),
        Achievement(
            name="历史学者",
            description="与红歌专家进行10次对话，你已经深入了解了不少红歌故事！",
            icon="📚",
            category="chat",
            condition_type="chat_messages",
            condition_value=10,
            points=100
        ),
        
        # 论坛类成就
        Achievement(
            name="初声发问",
            description="发表第1条论坛留言，开始和大家交流吧！",
            icon="💬",
            category="forum",
            condition_type="forum_posts",
            condition_value=1,
            points=40
        ),
        Achievement(
            name="社区活跃",
            description="发表5条论坛留言，你已经成为社区的活跃分子！",
            icon="💬",
            category="forum",
            condition_type="forum_posts",
            condition_value=5,
            points=80
        ),
        
        # 综合类成就
        Achievement(
            name="积分突破",
            description="累计获得100积分，你的努力没有白费！",
            icon="⭐",
            category="total",
            condition_type="total_score",
            condition_value=100,
            points=50
        ),
        Achievement(
            name="徽章达人",
            description="解锁5个成就徽章，你的成就之旅已经非常精彩！",
            icon="🏅",
            category="total",
            condition_type="achievement_count",
            condition_value=5,
            points=100
        ),
        Achievement(
            name="全能达人",
            description="解锁8个成就徽章，你在各个领域都有出色表现！",
            icon="🏅",
            category="total",
            condition_type="achievement_count",
            condition_value=8,
            points=200
        ),
        Achievement(
            name="巅峰王者",
            description="解锁所有11个成就徽章，你就是真正的红歌大师！",
            icon="👑",
            category="total",
            condition_type="achievement_count",
            condition_value=11,
            points=500
        )
    ]

    # 只添加数据库中不存在的成就
    added_count = 0
    for achievement in all_achievements:
        if achievement.name not in existing_achievement_names:
            db.session.add(achievement)
            added_count += 1
            print(f"添加成就: {achievement.name}")
    
    if added_count > 0:
        db.session.commit()
        print(f"共添加了 {added_count} 个新成就。")

    # 填充论坛帖子数据
    if not ForumPost.query.first() and User.query.first():
        default_user = User.query.first()
        posts = [
            ForumPost(user_id=default_user.id, content="红歌精神永流传！每一次听《义勇军进行曲》都热泪盈眶。"),
            ForumPost(user_id=default_user.id, content="这里整理的历史资料太详细了，学到了很多。"),
        ]
        db.session.bulk_save_objects(posts)
        db.session.commit()

    db.session.commit()
    print("数据库已初始化并填充了所有初始数据。")

def register_commands(app):
    """向Flask应用注册命令行"""
    @app.cli.command("init-db")
    def init_db_command():
        with app.app_context():
            init_db()


