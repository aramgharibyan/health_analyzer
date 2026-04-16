import React, { useEffect, useState, useCallback } from 'react';
import {
  ScrollView, View, Text, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator, Modal,
  TextInput, RefreshControl,
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import { labApi } from '../services/api';
import { LabTest } from '../types';

const STATUS_COLOR: Record<string, string> = {
  normal: '#4ade80',
  high: '#f59e0b',
  low: '#60a5fa',
  critical_high: '#ef4444',
  critical_low: '#ef4444',
};

export function LabTestsScreen() {
  const [tests, setTests] = useState<LabTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [testName, setTestName] = useState('');
  const [selectedFile, setSelectedFile] = useState<{ uri: string; name: string; type: string } | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const res = await labApi.list();
      setTests(res.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function pickDocument() {
    const result = await DocumentPicker.getDocumentAsync({
      type: ['application/pdf', 'image/*', 'text/plain'],
      copyToCacheDirectory: true,
    });
    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      setSelectedFile({ uri: asset.uri, name: asset.name, type: asset.mimeType ?? 'application/octet-stream' });
      setShowUploadModal(true);
    }
  }

  async function pickImage() {
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.9,
    });
    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      setSelectedFile({ uri: asset.uri, name: 'lab-test.jpg', type: 'image/jpeg' });
      setShowUploadModal(true);
    }
  }

  function showPickerOptions() {
    Alert.alert('Upload Lab Test', 'Choose source', [
      { text: 'Camera', onPress: pickImage },
      { text: 'Files (PDF/Image)', onPress: pickDocument },
      { text: 'Cancel', style: 'cancel' },
    ]);
  }

  async function uploadFile() {
    if (!selectedFile || !testName.trim()) {
      Alert.alert('Error', 'Please enter a test name.');
      return;
    }
    setUploading(true);
    setUploadProgress(0);
    try {
      await labApi.upload(
        selectedFile,
        { test_name: testName.trim() },
        (pct) => setUploadProgress(pct)
      );
      setShowUploadModal(false);
      setTestName('');
      setSelectedFile(null);
      await load();
    } catch (err: any) {
      Alert.alert('Upload Failed', err.response?.data?.detail ?? err.message);
    } finally {
      setUploading(false);
    }
  }

  async function deleteTest(id: number) {
    Alert.alert('Delete', 'Remove this lab test?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive',
        onPress: async () => {
          await labApi.delete(id);
          setTests((prev) => prev.filter((t) => t.id !== id));
        },
      },
    ]);
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#0ea5e9" />
      </View>
    );
  }

  return (
    <>
      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => load(true)} tintColor="#0ea5e9" />}
      >
        <TouchableOpacity style={styles.uploadBtn} onPress={showPickerOptions}>
          <Text style={styles.uploadBtnText}>+ Upload Lab Test</Text>
        </TouchableOpacity>

        {tests.length === 0 && (
          <Text style={styles.empty}>No lab tests yet. Upload a PDF or photo of your results.</Text>
        )}

        {tests.map((test) => (
          <View key={test.id} style={styles.card}>
            <TouchableOpacity
              style={styles.cardHeader}
              onPress={() => setExpanded(expanded === test.id ? null : test.id)}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.testName}>{test.test_name}</Text>
                {test.lab_name && <Text style={styles.meta}>{test.lab_name}</Text>}
                {test.test_date && (
                  <Text style={styles.meta}>{new Date(test.test_date).toLocaleDateString()}</Text>
                )}
              </View>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <View style={[styles.statusBadge, { backgroundColor: test.status === 'processed' ? '#052e16' : '#1c1917' }]}>
                  <Text style={styles.statusText}>{test.status}</Text>
                </View>
                <Text style={styles.chevron}>{expanded === test.id ? '▲' : '▼'}</Text>
              </View>
            </TouchableOpacity>

            {expanded === test.id && (
              <View style={styles.expanded}>
                {test.parsed_summary ? (
                  <Text style={styles.summary}>{test.parsed_summary}</Text>
                ) : null}

                {test.results.map((r) => (
                  <View key={r.id} style={styles.biomarkerRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.biomarkerName}>{r.biomarker_name}</Text>
                      {r.interpretation && (
                        <Text style={styles.interpretation}>{r.interpretation}</Text>
                      )}
                    </View>
                    <View style={{ alignItems: 'flex-end' }}>
                      <Text style={[styles.biomarkerValue, { color: STATUS_COLOR[r.status ?? ''] ?? '#e2e8f0' }]}>
                        {r.value ?? '—'} {r.unit}
                      </Text>
                      {r.reference_text && (
                        <Text style={styles.reference}>{r.reference_text}</Text>
                      )}
                    </View>
                  </View>
                ))}

                <TouchableOpacity style={styles.deleteBtn} onPress={() => deleteTest(test.id)}>
                  <Text style={styles.deleteBtnText}>Delete</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        ))}
      </ScrollView>

      {/* Upload modal */}
      <Modal visible={showUploadModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>Upload Lab Test</Text>
            {selectedFile && (
              <Text style={styles.fileName}>📄 {selectedFile.name}</Text>
            )}
            <TextInput
              style={styles.input}
              placeholder="Test name (e.g. Complete Blood Count)"
              placeholderTextColor="#64748b"
              value={testName}
              onChangeText={setTestName}
            />
            {uploading && (
              <View style={styles.progressBar}>
                <View style={[styles.progressFill, { width: `${uploadProgress}%` }]} />
              </View>
            )}
            <View style={styles.modalActions}>
              <TouchableOpacity
                style={[styles.btn, styles.btnSecondary]}
                onPress={() => { setShowUploadModal(false); setSelectedFile(null); setTestName(''); }}
                disabled={uploading}
              >
                <Text style={styles.btnSecondaryText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.btn, styles.btnPrimary]}
                onPress={uploadFile}
                disabled={uploading}
              >
                {uploading
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={styles.btnText}>Upload & Analyze</Text>
                }
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#0f172a' },
  content: { padding: 16 },
  center: { flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center' },
  uploadBtn: {
    backgroundColor: '#0ea5e9',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    marginBottom: 16,
  },
  uploadBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  empty: { color: '#64748b', textAlign: 'center', marginTop: 32, lineHeight: 22 },
  card: { backgroundColor: '#1e293b', borderRadius: 12, marginBottom: 12, overflow: 'hidden' },
  cardHeader: { flexDirection: 'row', padding: 16, alignItems: 'center' },
  testName: { color: '#e2e8f0', fontSize: 15, fontWeight: '600' },
  meta: { color: '#64748b', fontSize: 12, marginTop: 2 },
  statusBadge: { borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3 },
  statusText: { color: '#4ade80', fontSize: 11, fontWeight: '600' },
  chevron: { color: '#64748b', fontSize: 12 },
  expanded: { borderTopWidth: 1, borderTopColor: '#334155', padding: 16 },
  summary: { color: '#94a3b8', fontSize: 13, lineHeight: 20, marginBottom: 12 },
  biomarkerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#334155',
  },
  biomarkerName: { color: '#e2e8f0', fontSize: 14, fontWeight: '500' },
  interpretation: { color: '#64748b', fontSize: 11, marginTop: 2 },
  biomarkerValue: { fontSize: 15, fontWeight: '600' },
  reference: { color: '#475569', fontSize: 11 },
  deleteBtn: { marginTop: 12, padding: 8, alignItems: 'center' },
  deleteBtnText: { color: '#ef4444', fontSize: 13 },
  // Modal
  modalOverlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  modal: {
    backgroundColor: '#1e293b', borderTopLeftRadius: 20, borderTopRightRadius: 20,
    padding: 24, paddingBottom: 40,
  },
  modalTitle: { color: '#e2e8f0', fontSize: 18, fontWeight: '700', marginBottom: 16 },
  fileName: { color: '#94a3b8', fontSize: 13, marginBottom: 12 },
  input: {
    backgroundColor: '#0f172a',
    color: '#e2e8f0',
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  progressBar: {
    height: 4, backgroundColor: '#334155', borderRadius: 2, marginBottom: 16, overflow: 'hidden',
  },
  progressFill: { height: 4, backgroundColor: '#0ea5e9', borderRadius: 2 },
  modalActions: { flexDirection: 'row', gap: 8 },
  btn: { flex: 1, borderRadius: 10, padding: 14, alignItems: 'center' },
  btnPrimary: { backgroundColor: '#0ea5e9' },
  btnSecondary: { backgroundColor: '#334155' },
  btnText: { color: '#fff', fontWeight: '700' },
  btnSecondaryText: { color: '#94a3b8', fontWeight: '600' },
});
