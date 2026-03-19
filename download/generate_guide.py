#!/usr/bin/env python3
"""
Генератор PDF документации для StarLine Collector
"""

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
import os

# Регистрация шрифтов
pdfmetrics.registerFont(TTFont('SimHei', '/usr/share/fonts/truetype/chinese/SimHei.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'))

registerFontFamily('SimHei', normal='SimHei', bold='SimHei')
registerFontFamily('Times New Roman', normal='Times New Roman', bold='Times New Roman')

def create_styles():
    styles = getSampleStyleSheet()
    
    # Заголовок документа
    styles.add(ParagraphStyle(
        name='DocTitle',
        fontName='SimHei',
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#1F4E79')
    ))
    
    # Подзаголовок
    styles.add(ParagraphStyle(
        name='DocSubtitle',
        fontName='SimHei',
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=colors.HexColor('#666666')
    ))
    
    # Заголовок раздела (H1)
    styles.add(ParagraphStyle(
        name='SectionTitle',
        fontName='SimHei',
        fontSize=16,
        leading=22,
        alignment=TA_LEFT,
        spaceBefore=20,
        spaceAfter=12,
        textColor=colors.HexColor('#1F4E79'),
        borderPadding=(5, 0, 5, 0),
        borderWidth=0,
        borderColor=colors.HexColor('#1F4E79')
    ))
    
    # Заголовок подраздела (H2)
    styles.add(ParagraphStyle(
        name='SubsectionTitle',
        fontName='SimHei',
        fontSize=13,
        leading=18,
        alignment=TA_LEFT,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#2E75B6')
    ))
    
    # Заголовок шага (H3)
    styles.add(ParagraphStyle(
        name='StepTitle',
        fontName='SimHei',
        fontSize=11,
        leading=15,
        alignment=TA_LEFT,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor('#333333')
    ))
    
    # Основной текст
    styles.add(ParagraphStyle(
        name='BodyText',
        fontName='SimHei',
        fontSize=10,
        leading=15,
        alignment=TA_LEFT,
        spaceAfter=8,
        wordWrap='CJK'
    ))
    
    # Код
    styles.add(ParagraphStyle(
        name='Code',
        fontName='DejaVuSans',
        fontSize=8,
        leading=11,
        alignment=TA_LEFT,
        spaceAfter=6,
        backColor=colors.HexColor('#F5F5F5'),
        leftIndent=10,
        rightIndent=10,
        borderPadding=5
    ))
    
    # Примечание
    styles.add(ParagraphStyle(
        name='Note',
        fontName='SimHei',
        fontSize=9,
        leading=13,
        alignment=TA_LEFT,
        spaceAfter=8,
        backColor=colors.HexColor('#FFF3CD'),
        leftIndent=10,
        rightIndent=10,
        borderPadding=8,
        textColor=colors.HexColor('#856404')
    ))
    
    # Текст в таблице
    styles.add(ParagraphStyle(
        name='TableCell',
        fontName='SimHei',
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
        wordWrap='CJK'
    ))
    
    # Заголовок таблицы
    styles.add(ParagraphStyle(
        name='TableHeader',
        fontName='SimHei',
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.white
    ))
    
    return styles

def build_document():
    output_path = '/home/z/my-project/download/StarLine_Collector_Guide.pdf'
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title='StarLine Collector - Руководство по установке',
        author='Z.ai',
        creator='Z.ai',
        subject='Пошаговое руководство по развёртыванию приложения для сбора данных StarLine'
    )
    
    styles = create_styles()
    story = []
    
    # ==========================================================================
    # ТИТУЛЬНАЯ СТРАНИЦА
    # ==========================================================================
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph('StarLine Data Collector', styles['DocTitle']))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph('Пошаговое руководство по развёртыванию на Ubuntu Server', styles['DocSubtitle']))
    story.append(Spacer(1, 2*cm))
    
    # Информация о документе
    info_data = [
        [Paragraph('<b>Версия документа</b>', styles['TableCell']), Paragraph('1.0', styles['TableCell'])],
        [Paragraph('<b>Дата создания</b>', styles['TableCell']), Paragraph('2025-01-18', styles['TableCell'])],
        [Paragraph('<b>Поддерживаемая ОС</b>', styles['TableCell']), Paragraph('Ubuntu Server 20.04/22.04/24.04', styles['TableCell'])],
        [Paragraph('<b>Требуемые компоненты</b>', styles['TableCell']), Paragraph('Python 3.8+, MySQL 8.0+', styles['TableCell'])],
    ]
    
    info_table = Table(info_data, colWidths=[5*cm, 8*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    
    story.append(PageBreak())
    
    # ==========================================================================
    # СОДЕРЖАНИЕ
    # ==========================================================================
    story.append(Paragraph('Содержание', styles['SectionTitle']))
    story.append(Spacer(1, 0.5*cm))
    
    toc_items = [
        '1. Введение и обзор StarLine API',
        '2. Предварительные требования',
        '3. Установка MySQL Server',
        '4. Создание базы данных и пользователя',
        '5. Получение доступа к StarLine API',
        '6. Установка Python и зависимостей',
        '7. Развёртывание приложения',
        '8. Настройка конфигурации',
        '9. Запуск и тестирование',
        '10. Настройка systemd-сервиса',
        '11. Примеры SQL-запросов',
        '12. Мониторинг и устранение неполадок',
    ]
    
    for item in toc_items:
        story.append(Paragraph(item, styles['BodyText']))
    
    story.append(PageBreak())
    
    # ==========================================================================
    # РАЗДЕЛ 1: ВВЕДЕНИЕ
    # ==========================================================================
    story.append(Paragraph('1. Введение и обзор StarLine API', styles['SectionTitle']))
    
    story.append(Paragraph(
        'Данное руководство описывает процесс развёртывания приложения для автоматического сбора '
        'данных телематической сигнализации StarLine и их сохранения в базу данных MySQL. '
        'Приложение позволяет собирать информацию о состоянии охраны, температуре, местоположении '
        'GPS, данных OBD-II и других показателях автомобиля.',
        styles['BodyText']
    ))
    
    story.append(Paragraph('1.1 Архитектура решения', styles['SubsectionTitle']))
    
    story.append(Paragraph(
        'Приложение работает по следующей схеме: сначала выполняется авторизация в API StarLine '
        'через сервис StarLineID (SLID), затем получается токен доступа к WebAPI. С помощью этого '
        'токена приложение периодически опрашивает состояние всех привязанных устройств и сохраняет '
        'полученные данные в MySQL базу данных для последующего анализа и визуализации.',
        styles['BodyText']
    ))
    
    story.append(Paragraph('1.2 Доступные данные', styles['SubsectionTitle']))
    
    # Таблица доступных данных
    data_table = [
        [Paragraph('<b>Категория</b>', styles['TableHeader']), 
         Paragraph('<b>Параметры</b>', styles['TableHeader']),
         Paragraph('<b>Описание</b>', styles['TableHeader'])],
        [Paragraph('Состояние охраны', styles['TableCell']),
         Paragraph('arm_state, arm_datetime', styles['TableCell']),
         Paragraph('Режим охраны, время последнего изменения', styles['TableCell'])],
        [Paragraph('Двигатель', styles['TableCell']),
         Paragraph('ign_state, run_time', styles['TableCell']),
         Paragraph('Состояние зажигания, время работы', styles['TableCell'])],
        [Paragraph('Температура', styles['TableCell']),
         Paragraph('temp_inner, temp_engine, temp_outdoor', styles['TableCell']),
         Paragraph('Температура в салоне, двигателя, на улице', styles['TableCell'])],
        [Paragraph('GPS', styles['TableCell']),
         Paragraph('latitude, longitude, speed, course', styles['TableCell']),
         Paragraph('Координаты, скорость, направление', styles['TableCell'])],
        [Paragraph('OBD-II', styles['TableCell']),
         Paragraph('fuel_level, mileage, engine_rpm', styles['TableCell']),
         Paragraph('Уровень топлива, пробег, обороты', styles['TableCell'])],
        [Paragraph('Двери', styles['TableCell']),
         Paragraph('door_driver, hood, trunk', styles['TableCell']),
         Paragraph('Состояние дверей, капота, багажника', styles['TableCell'])],
    ]
    
    t = Table(data_table, colWidths=[3.5*cm, 5*cm, 6*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#F5F5F5')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.white),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#F5F5F5')),
        ('BACKGROUND', (0, 5), (-1, 5), colors.white),
        ('BACKGROUND', (0, 6), (-1, 6), colors.HexColor('#F5F5F5')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(Spacer(1, 0.3*cm))
    story.append(t)
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph('1.3 Ограничения API', styles['SubsectionTitle']))
    
    story.append(Paragraph(
        'Важно учитывать ограничения StarLine API для физических лиц: максимум 1000 запросов в день '
        'на одного пользователя. При интервале опроса 5 минут (300 секунд) приложение выполняет '
        '288 запросов в сутки, что укладывается в лимит. Также есть ограничения на запрос треков '
        'GPS: интервал не более 24 часов, запросы не чаще чем раз в 10 минут.',
        styles['BodyText']
    ))
    
    # ==========================================================================
    # РАЗДЕЛ 2: ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ
    # ==========================================================================
    story.append(Paragraph('2. Предварительные требования', styles['SectionTitle']))
    
    story.append(Paragraph(
        'Перед началом установки убедитесь, что ваш сервер соответствует минимальным требованиям '
        'и у вас есть все необходимые данные для авторизации в StarLine API.',
        styles['BodyText']
    ))
    
    story.append(Paragraph('2.1 Системные требования', styles['SubsectionTitle']))
    
    req_table = [
        [Paragraph('<b>Компонент</b>', styles['TableHeader']),
         Paragraph('<b>Минимум</b>', styles['TableHeader']),
         Paragraph('<b>Рекомендуется</b>', styles['TableHeader'])],
        [Paragraph('Оперативная память', styles['TableCell']),
         Paragraph('1 GB', styles['TableCell']),
         Paragraph('2 GB', styles['TableCell'])],
        [Paragraph('Дисковое пространство', styles['TableCell']),
         Paragraph('10 GB', styles['TableCell']),
         Paragraph('20 GB', styles['TableCell'])],
        [Paragraph('Python', styles['TableCell']),
         Paragraph('3.8', styles['TableCell']),
         Paragraph('3.10+', styles['TableCell'])],
        [Paragraph('MySQL', styles['TableCell']),
         Paragraph('8.0', styles['TableCell']),
         Paragraph('8.0+', styles['TableCell'])],
    ]
    
    t2 = Table(req_table, colWidths=[5*cm, 4.5*cm, 5*cm])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(Spacer(1, 0.3*cm))
    story.append(t2)
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph('2.2 Необходимые данные', styles['SubsectionTitle']))
    
    story.append(Paragraph(
        'Для работы с API вам понадобятся следующие данные, которые можно получить на портале '
        'my.starline.ru в разделе "Разработчикам" (раздел доступен только при выборе русского '
        'языка интерфейса):',
        styles['BodyText']
    ))
    
    creds_list = [
        'AppId — идентификатор приложения (выдаётся после создания приложения)',
        'Secret — пароль приложения (секретный ключ)',
        'Логин пользователя — email или телефон, привязанный к аккаунту StarLine',
        'Пароль пользователя — пароль от личного кабинета StarLine',
    ]
    
    for item in creds_list:
        story.append(Paragraph(f'• {item}', styles['BodyText']))
    
    # ==========================================================================
    # РАЗДЕЛ 3: УСТАНОВКА MYSQL
    # ==========================================================================
    story.append(Paragraph('3. Установка MySQL Server', styles['SectionTitle']))
    
    story.append(Paragraph('Шаг 3.1: Обновление системы', styles['StepTitle']))
    story.append(Paragraph('sudo apt update && sudo apt upgrade -y', styles['Code']))
    
    story.append(Paragraph('Шаг 3.2: Установка MySQL Server', styles['StepTitle']))
    story.append(Paragraph('sudo apt install mysql-server -y', styles['Code']))
    
    story.append(Paragraph('Шаг 3.3: Безопасная настройка MySQL', styles['StepTitle']))
    story.append(Paragraph(
        'sudo mysql_secure_installation',
        styles['Code']
    ))
    story.append(Paragraph(
        'Следуйте инструкциям: установите пароль root, удалите анонимных пользователей, '
        'запретите удалённый вход root, удалите тестовую базу данных.',
        styles['BodyText']
    ))
    
    story.append(Paragraph('Шаг 3.4: Проверка статуса', styles['StepTitle']))
    story.append(Paragraph('sudo systemctl status mysql', styles['Code']))
    story.append(Paragraph(
        'Убедитесь, что сервис активен (active/running).',
        styles['BodyText']
    ))
    
    # ==========================================================================
    # РАЗДЕЛ 4: СОЗДАНИЕ БАЗЫ ДАННЫХ
    # ==========================================================================
    story.append(Paragraph('4. Создание базы данных и пользователя', styles['SectionTitle']))
    
    story.append(Paragraph('Шаг 4.1: Подключение к MySQL', styles['StepTitle']))
    story.append(Paragraph('sudo mysql -u root -p', styles['Code']))
    
    story.append(Paragraph('Шаг 4.2: Создание базы данных и пользователя', styles['StepTitle']))
    story.append(Paragraph(
        "CREATE DATABASE starline_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
        "CREATE USER 'starline'@'localhost' IDENTIFIED BY 'ВАШ_НАДЁЖНЫЙ_ПАРОЛЬ';\n"
        "GRANT ALL PRIVILEGES ON starline_db.* TO 'starline'@'localhost';\n"
        "FLUSH PRIVILEGES;",
        styles['Code']
    ))
    
    story.append(Paragraph(
        'ВАЖНО: Замените "ВАШ_НАДЁЖНЫЙ_ПАРОЛЬ" на надёжный пароль. '
        'Сохраните его — он понадобится при настройке приложения.',
        styles['Note']
    ))
    
    story.append(Paragraph('Шаг 4.3: Создание структуры таблиц', styles['StepTitle']))
    story.append(Paragraph(
        'Выйдите из MySQL (команда exit) и выполните SQL-скрипт init_database.sql, '
        'который находится в архиве с приложением:',
        styles['BodyText']
    ))
    story.append(Paragraph('mysql -u starline -p starline_db < init_database.sql', styles['Code']))
    
    # ==========================================================================
    # РАЗДЕЛ 5: ПОЛУЧЕНИЕ ДОСТУПА К API
    # ==========================================================================
    story.append(Paragraph('5. Получение доступа к StarLine API', styles['SectionTitle']))
    
    story.append(Paragraph('Шаг 5.1: Регистрация на портале', styles['StepTitle']))
    story.append(Paragraph(
        '1. Перейдите на сайт my.starline.ru и войдите в личный кабинет\n'
        '2. В настройках профиля выберите русский язык интерфейса\n'
        '3. В меню появится раздел "Разработчикам"',
        styles['BodyText']
    ))
    
    story.append(Paragraph('Шаг 5.2: Создание приложения', styles['StepTitle']))
    story.append(Paragraph(
        '1. Нажмите кнопку "Создать приложение"\n'
        '2. Заполните форму (название, описание, цель использования)\n'
        '3. Дождитесь одобрения заявки (обычно 1-3 рабочих дня)\n'
        '4. После одобрения вы получите AppId и Secret',
        styles['BodyText']
    ))
    
    story.append(Paragraph(
        'Без одобрения заявки вы не сможете использовать API. Обязательно '
        'опишите реальную цель использования — заявки без описания не рассматриваются.',
        styles['Note']
    ))
    
    # ==========================================================================
    # РАЗДЕЛ 6: УСТАНОВКА PYTHON
    # ==========================================================================
    story.append(Paragraph('6. Установка Python и зависимостей', styles['SectionTitle']))
    
    story.append(Paragraph('Шаг 6.1: Установка Python 3 и pip', styles['StepTitle']))
    story.append(Paragraph('sudo apt install python3 python3-pip python3-venv -y', styles['Code']))
    
    story.append(Paragraph('Шаг 6.2: Создание директории приложения', styles['StepTitle']))
    story.append(Paragraph(
        'sudo mkdir -p /opt/starline-collector\n'
        'sudo chown $USER:$USER /opt/starline-collector',
        styles['Code']
    ))
    
    story.append(Paragraph('Шаг 6.3: Создание виртуального окружения', styles['StepTitle']))
    story.append(Paragraph(
        'cd /opt/starline-collector\n'
        'python3 -m venv venv\n'
        'source venv/bin/activate',
        styles['Code']
    ))
    
    story.append(Paragraph('Шаг 6.4: Установка зависимостей', styles['StepTitle']))
    story.append(Paragraph(
        'pip install requests mysql-connector-python',
        styles['Code']
    ))
    
    # ==========================================================================
    # РАЗДЕЛ 7: РАЗВЁРТЫВАНИЕ ПРИЛОЖЕНИЯ
    # ==========================================================================
    story.append(Paragraph('7. Развёртывание приложения', styles['SectionTitle']))
    
    story.append(Paragraph('Шаг 7.1: Копирование файлов', styles['StepTitle']))
    story.append(Paragraph(
        'Скопируйте файлы приложения в директорию /opt/starline-collector:\n'
        '- collector.py (основной скрипт)\n'
        '- config.json (конфигурация)',
        styles['BodyText']
    ))
    
    story.append(Paragraph('Шаг 7.2: Создание директории для конфигурации', styles['StepTitle']))
    story.append(Paragraph(
        'sudo mkdir -p /etc/starline-collector\n'
        'sudo chown $USER:$USER /etc/starline-collector',
        styles['Code']
    ))
    
    story.append(Paragraph('Шаг 7.3: Создание директории для логов', styles['StepTitle']))
    story.append(Paragraph(
        'sudo touch /var/log/starline_collector.log\n'
        'sudo chown $USER:$USER /var/log/starline_collector.log',
        styles['Code']
    ))
    
    # ==========================================================================
    # РАЗДЕЛ 8: НАСТРОЙКА КОНФИГУРАЦИИ
    # ==========================================================================
    story.append(Paragraph('8. Настройка конфигурации', styles['SectionTitle']))
    
    story.append(Paragraph('Шаг 8.1: Создание файла конфигурации', styles['StepTitle']))
    story.append(Paragraph(
        'nano /etc/starline-collector/config.json',
        styles['Code']
    ))
    
    story.append(Paragraph('Шаг 8.2: Пример содержимого config.json', styles['StepTitle']))
    story.append(Paragraph(
        '{\n'
        '    "app_id": "ВАШ_APP_ID",\n'
        '    "app_secret": "ВАШ_SECRET",\n'
        '    "user_login": "ваш_email@example.com",\n'
        '    "user_password": "ВАШ_ПАРОЛЬ_STARLINE",\n'
        '    "mysql_host": "localhost",\n'
        '    "mysql_port": 3306,\n'
        '    "mysql_user": "starline",\n'
        '    "mysql_password": "ВАШ_ПАРОЛЬ_MYSQL",\n'
        '    "mysql_database": "starline_db",\n'
        '    "poll_interval_seconds": 300\n'
        '}',
        styles['Code']
    ))
    
    story.append(Paragraph('Шаг 8.3: Ограничение прав доступа', styles['StepTitle']))
    story.append(Paragraph(
        'chmod 600 /etc/starline-collector/config.json',
        styles['Code']
    ))
    story.append(Paragraph(
        'Файл конфигурации содержит пароли, поэтому доступ к нему должен быть ограничен.',
        styles['Note']
    ))
    
    # ==========================================================================
    # РАЗДЕЛ 9: ЗАПУСК И ТЕСТИРОВАНИЕ
    # ==========================================================================
    story.append(Paragraph('9. Запуск и тестирование', styles['SectionTitle']))
    
    story.append(Paragraph('Шаг 9.1: Тестовый запуск (однократный сбор)', styles['StepTitle']))
    story.append(Paragraph(
        'cd /opt/starline-collector\n'
        'source venv/bin/activate\n'
        'python collector.py --once',
        styles['Code']
    ))
    
    story.append(Paragraph('Шаг 9.2: Проверка данных в базе', styles['StepTitle']))
    story.append(Paragraph(
        'mysql -u starline -p starline_db -e "SELECT * FROM devices;"\n'
        'mysql -u starline -p starline_db -e "SELECT COUNT(*) FROM alarm_states;"',
        styles['Code']
    ))
    
    story.append(Paragraph('Шаг 9.3: Запуск в режиме демона (тестовый)', styles['StepTitle']))
    story.append(Paragraph(
        'python collector.py -d',
        styles['Code']
    ))
    story.append(Paragraph(
        'Для остановки нажмите Ctrl+C. Убедитесь, что данные регулярно поступают в базу.',
        styles['BodyText']
    ))
    
    # ==========================================================================
    # РАЗДЕЛ 10: НАСТРОЙКА SYSTEMD
    # ==========================================================================
    story.append(Paragraph('10. Настройка systemd-сервиса', styles['SectionTitle']))
    
    story.append(Paragraph('Шаг 10.1: Создание пользователя для сервиса', styles['StepTitle']))
    story.append(Paragraph(
        'sudo useradd -r -s /bin/false starline\n'
        'sudo chown -R starline:starline /opt/starline-collector\n'
        'sudo chown starline:starline /var/log/starline_collector.log',
        styles['Code']
    ))
    
    story.append(Paragraph('Шаг 10.2: Создание unit-файла', styles['StepTitle']))
    story.append(Paragraph(
        'sudo nano /etc/systemd/system/starline-collector.service',
        styles['Code']
    ))
    
    story.append(Paragraph('Шаг 10.3: Содержимое unit-файла', styles['StepTitle']))
    story.append(Paragraph(
        '[Unit]\n'
        'Description=StarLine Data Collector Service\n'
        'After=network.target mysql.service\n\n'
        '[Service]\n'
        'Type=simple\n'
        'User=starline\n'
        'Group=starline\n'
        'WorkingDirectory=/opt/starline-collector\n'
        'ExecStart=/opt/starline-collector/venv/bin/python collector.py -d\n'
        'Restart=on-failure\n'
        'RestartSec=10\n\n'
        '[Install]\n'
        'WantedBy=multi-user.target',
        styles['Code']
    ))
    
    story.append(Paragraph('Шаг 10.4: Активация и запуск сервиса', styles['StepTitle']))
    story.append(Paragraph(
        'sudo systemctl daemon-reload\n'
        'sudo systemctl enable starline-collector\n'
        'sudo systemctl start starline-collector',
        styles['Code']
    ))
    
    story.append(Paragraph('Шаг 10.5: Проверка статуса', styles['StepTitle']))
    story.append(Paragraph(
        'sudo systemctl status starline-collector\n'
        'sudo journalctl -u starline-collector -f',
        styles['Code']
    ))
    
    # ==========================================================================
    # РАЗДЕЛ 11: ПРИМЕРЫ SQL-ЗАПРОСОВ
    # ==========================================================================
    story.append(Paragraph('11. Примеры SQL-запросов', styles['SectionTitle']))
    
    story.append(Paragraph('11.1 Последнее состояние всех устройств', styles['SubsectionTitle']))
    story.append(Paragraph(
        "SELECT d.name, a.timestamp, a.arm_state, a.ign_state,\n"
        "       a.temp_inner, a.temp_engine, a.balance\n"
        "FROM alarm_states a\n"
        "JOIN devices d ON a.device_id = d.device_id\n"
        "WHERE a.timestamp = (\n"
        "    SELECT MAX(timestamp) FROM alarm_states WHERE device_id = a.device_id\n"
        ");",
        styles['Code']
    ))
    
    story.append(Paragraph('11.2 История GPS-позиций за период', styles['SubsectionTitle']))
    story.append(Paragraph(
        "SELECT timestamp, latitude, longitude, speed, course\n"
        "FROM gps_positions\n"
        "WHERE device_id = 'DEVICE_ID'\n"
        "AND timestamp BETWEEN '2025-01-01' AND '2025-01-31'\n"
        "ORDER BY timestamp;",
        styles['Code']
    ))
    
    story.append(Paragraph('11.3 Средний расход топлива за месяц', styles['SubsectionTitle']))
    story.append(Paragraph(
        "SELECT d.name, AVG(o.fuel_consumption) as avg_consumption\n"
        "FROM obd_data o\n"
        "JOIN devices d ON o.device_id = d.device_id\n"
        "WHERE o.timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)\n"
        "GROUP BY d.device_id;",
        styles['Code']
    ))
    
    story.append(Paragraph('11.4 Активные ошибки OBD', styles['SubsectionTitle']))
    story.append(Paragraph(
        "SELECT d.name, e.error_code, e.error_description, e.timestamp\n"
        "FROM obd_errors e\n"
        "JOIN devices d ON e.device_id = d.device_id\n"
        "WHERE e.is_active = 1\n"
        "ORDER BY e.timestamp DESC;",
        styles['Code']
    ))
    
    # ==========================================================================
    # РАЗДЕЛ 12: МОНИТОРИНГ
    # ==========================================================================
    story.append(Paragraph('12. Мониторинг и устранение неполадок', styles['SectionTitle']))
    
    story.append(Paragraph('12.1 Просмотр логов', styles['SubsectionTitle']))
    story.append(Paragraph(
        'tail -f /var/log/starline_collector.log\n'
        'sudo journalctl -u starline-collector -n 100',
        styles['Code']
    ))
    
    story.append(Paragraph('12.2 Типичные проблемы', styles['SubsectionTitle']))
    
    problems_table = [
        [Paragraph('<b>Проблема</b>', styles['TableHeader']),
         Paragraph('<b>Возможная причина</b>', styles['TableHeader']),
         Paragraph('<b>Решение</b>', styles['TableHeader'])],
        [Paragraph('Ошибка авторизации', styles['TableCell']),
         Paragraph('Неверные AppId/Secret', styles['TableCell']),
         Paragraph('Проверьте данные в config.json', styles['TableCell'])],
        [Paragraph('Нет данных в БД', styles['TableCell']),
         Paragraph('Ошибка подключения к MySQL', styles['TableCell']),
         Paragraph('Проверьте пароль и права пользователя', styles['TableCell'])],
        [Paragraph('API возвращает ошибку', styles['TableCell']),
         Paragraph('Превышен лимит запросов', styles['TableCell']),
         Paragraph('Увеличьте poll_interval_seconds', styles['TableCell'])],
        [Paragraph('Двухфакторная аутентификация', styles['TableCell']),
         Paragraph('Включена 2FA в StarLine', styles['TableCell']),
         Paragraph('Отключите 2FA или добавьте обработку SMS', styles['TableCell'])],
    ]
    
    pt = Table(problems_table, colWidths=[4*cm, 5*cm, 5.5*cm])
    pt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#F5F5F5')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.white),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#F5F5F5')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(Spacer(1, 0.3*cm))
    story.append(pt)
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph('12.3 Полезные команды', styles['SubsectionTitle']))
    story.append(Paragraph(
        '# Перезапуск сервиса\n'
        'sudo systemctl restart starline-collector\n\n'
        '# Проверка количества записей за сегодня\n'
        'mysql -u starline -p -e "SELECT COUNT(*) FROM alarm_states WHERE DATE(timestamp) = CURDATE();" starline_db\n\n'
        '# Ручной запуск сбора\n'
        'sudo -u starline /opt/starline-collector/venv/bin/python /opt/starline-collector/collector.py --once',
        styles['Code']
    ))
    
    # ==========================================================================
    # ЗАКЛЮЧЕНИЕ
    # ==========================================================================
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        'Данное руководство описывает базовую конфигурацию приложения. Для дополнительной '
        'информации о StarLine API обратитесь к официальной документации: '
        'https://developer.starline.ru/',
        styles['BodyText']
    ))
    
    # Сборка документа
    doc.build(story)
    print(f"PDF создан: {output_path}")

if __name__ == '__main__':
    build_document()
