import React, { useState, useRef, useEffect } from 'react';
import {
  Card, Text, TextInput, ActionIcon, Stack, Group, ScrollArea, Box,
  ThemeIcon, Loader,
} from '@mantine/core';
import { IconSend, IconSparkles, IconUser } from '@tabler/icons-react';
import axios from 'axios';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export const AssistantTab: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'Hello! I\'m your personal stylist. Ask me anything about outfit ideas, what to wear, or styling tips based on your wardrobe.' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const viewport = useRef<HTMLDivElement>(null);

  useEffect(() => {
    viewport.current?.scrollTo({ top: viewport.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const res = await axios.post<{ reply: string }>('/api/chat/message', { message: text });
      setMessages((prev) => [...prev, { role: 'assistant', content: res.data.reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I couldn\'t process that. The chat backend may not be running yet.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      withBorder
      radius="md"
      p={0}
      className="stylist-chat-card"
    >
      {/* Messages area */}
      <ScrollArea flex={1} p="md" viewportRef={viewport}>
        <Stack gap="md">
          {messages.map((msg, i) => (
            <Group
              key={i}
              align="flex-start"
              gap="sm"
              style={{
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
              }}
            >
              <ThemeIcon
                size="md"
                radius="xl"
                variant={msg.role === 'user' ? 'light' : 'filled'}
                color={msg.role === 'user' ? 'gray' : 'amber'}
                mt={4}
              >
                {msg.role === 'user' ? <IconUser size={14} /> : <IconSparkles size={14} />}
              </ThemeIcon>
              <Box
                className={msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'}
              >
                <Text style={{ whiteSpace: 'pre-wrap' }}>
                  {msg.content}
                </Text>
              </Box>
            </Group>
          ))}
          {loading && (
            <Group gap="sm">
              <ThemeIcon size="md" radius="xl" variant="filled" color="amber" mt={4}>
                <IconSparkles size={14} />
              </ThemeIcon>
              <Loader size="xs" color="amber" type="dots" />
            </Group>
          )}
        </Stack>
      </ScrollArea>

      {/* Input area */}
      <Box
        p="md"
        className="stylist-chat-input-area"
      >
        <Group gap="xs">
          <TextInput
            flex={1}
            placeholder="Ask your stylist…"
            value={input}
            onChange={(e) => setInput(e.currentTarget.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            disabled={loading}
            radius="xl"
            size="md"
          />
          <ActionIcon
            size="lg"
            radius="xl"
            variant="filled"
            color="amber"
            onClick={send}
            disabled={loading || !input.trim()}
          >
            <IconSend size={16} />
          </ActionIcon>
        </Group>
      </Box>
    </Card>
  );
};
