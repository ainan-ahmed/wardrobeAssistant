import React, { useState, useRef, useEffect } from 'react';
import {
  Card, Text, TextInput, ActionIcon, Stack, Group, ScrollArea, Box,
  ThemeIcon, Loader,
} from '@mantine/core';
import { IconSend, IconSparkles, IconUser } from '@tabler/icons-react';

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
      const history = messages.slice(1).concat({ role: 'user', content: text });
      
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: text, history }),
      });

      if (!response.ok || !response.body) {
        throw new Error('Network response was not ok');
      }

      setLoading(false); // Stop loader once chunks begin streaming
      
      // Append initial blank assistant message to stream into
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;
      let accumulatedResponse = '';
      let buffer = '';

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          buffer += decoder.decode(value, { stream: !done });
          const lines = buffer.split('\n');
          // Save the last element (potential partial line segment) back into the buffer
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('data: ')) {
              const dataStr = trimmed.slice(6);
              try {
                const data = JSON.parse(dataStr);
                if (data.chunk) {
                  accumulatedResponse += data.chunk;
                  setMessages((prev) => {
                    const next = [...prev];
                    if (next.length > 0) {
                      next[next.length - 1] = {
                        role: 'assistant',
                        content: accumulatedResponse,
                      };
                    }
                    return next;
                  });
                } else if (data.error) {
                  console.error('Stylist stream error:', data.error);
                }
              } catch (e) {
                console.error('Failed to parse SSE JSON line:', e, line);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error('Streaming request failed:', err);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I couldn\'t process that. The streaming chat backend might not be running yet.' },
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
