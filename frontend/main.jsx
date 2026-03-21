import { useEffect } from "react";
import { createChat } from "@n8n/chat";
import "@n8n/chat/style.css";

const WEBHOOK_URL = "/webhook/fa4c959d-c7b4-4920-ad91-241f53b458a4/chat";

export default function App() {
  useEffect(() => {
    createChat({
      webhookUrl: WEBHOOK_URL,
      mode: "fullscreen",
      showWelcomeScreen: true,
      initialMessages: [
        "Здравствуйте! Я ассистент по технической документации.",
        "Задайте вопрос по паспортам оборудования или нормативным документам (ФЗ-116).",
      ],
      i18n: {
        en: {
          title: "Ассистент ОПО",
          subtitle: "Идентификация опасных производственных объектов",
          inputPlaceholder: "Задайте вопрос...",
          getStarted: "Начать",
          closeButtonTooltip: "Закрыть",
        },
      },
    });
  }, []);

  return <div />;
}