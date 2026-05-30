import React, { useState } from 'react';
import { Card, Text, TextInput, Flex, Stack } from '@mantine/core';
import { Dropzone, IMAGE_MIME_TYPE, FileWithPath } from '@mantine/dropzone';

interface ApparelIngestionProps {
  onUpload: (files: FileWithPath[], brand: string) => void;
  loading: boolean;
  uploadError: string | null;
}

export const ApparelIngestion: React.FC<ApparelIngestionProps> = ({ onUpload, loading, uploadError }) => {
  const [brand, setBrand] = useState<string>('');

  const handleDrop = (files: FileWithPath[]) => {
    if (files.length === 0) return;
    onUpload(files, brand);
    setBrand('');
  };

  return (
    <Card className="bento-card" p="xl" radius="lg">
      <Text className="editorial-header" size="xs" c="dimmed" fw={700} mb="md">
        Ingest Apparel
      </Text>
      
      <TextInput
        label="Brand Name"
        placeholder="e.g., APC, Levi's, Celine"
        value={brand}
        onChange={(event) => setBrand(event.currentTarget.value)}
        mb="md"
        variant="filled"
        styles={{
          input: {
            border: '1px solid rgba(197, 138, 62, 0.15)',
            backgroundColor: 'rgba(255, 255, 255, 0.4)',
            transition: 'var(--transition-smooth)',
            '&:focus': {
              borderColor: 'var(--amber-primary)'
            }
          }
        }}
      />
      
      <Dropzone
        onDrop={handleDrop}
        maxSize={5 * 1024 ** 2} // 5MB Limit
        accept={IMAGE_MIME_TYPE}
        loading={loading}
        radius="md"
        styles={{
          root: {
            border: '1px dashed var(--amber-primary)',
            backgroundColor: 'var(--amber-glow)',
            transition: 'var(--transition-smooth)',
            '&:hover': {
              backgroundColor: 'rgba(197, 138, 62, 0.08)',
              transform: 'scale(1.01)'
            }
          }
        }}
      >
        <Flex justify="center" align="center" direction="column" gap="xs" mih={140} style={{ pointerEvents: 'none', textAlign: 'center' }}>
          <Dropzone.Accept>
            <Text size="md" fw={600} c="amber">Drop to catalog...</Text>
          </Dropzone.Accept>
          <Dropzone.Reject>
            <Text size="md" fw={600} c="red">Accepts only image formats</Text>
          </Dropzone.Reject>
          <Dropzone.Idle>
            <Stack align="center" gap={4}>
              <Text size="2xl" inline>📸</Text>
              <Text size="sm" fw={500} mt={8} c="amber">
                Drop garment picture here
              </Text>
              <Text size="xs" c="dimmed">
                PNG or JPG (isolated in background)
              </Text>
            </Stack>
          </Dropzone.Idle>
        </Flex>
      </Dropzone>

      {uploadError && (
        <Text color="red" size="xs" mt="md" style={{ textAlign: 'center' }}>
          ⚠️ {uploadError}
        </Text>
      )}
    </Card>
  );
};
