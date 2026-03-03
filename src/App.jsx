import { useState, useRef, useCallback, useEffect } from 'react'
import Dashboard from './components/Dashboard'
import './App.css'

function App() {
    const [isDragging, setIsDragging] = useState(false)
    const [file, setFile] = useState(null)
    const [isAnalyzing, setIsAnalyzing] = useState(false)
    const [error, setError] = useState(null)
    const [analysisResult, setAnalysisResult] = useState(null)
    const fileInputRef = useRef(null)

    const handleDragEnter = useCallback((e) => {
        e.preventDefault()
        e.stopPropagation()
        if (!isAnalyzing) setIsDragging(true)
    }, [isAnalyzing])

    const handleDragLeave = useCallback((e) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)
    }, [])

    const handleDragOver = useCallback((e) => {
        e.preventDefault()
        e.stopPropagation()
        if (!isDragging && !isAnalyzing) setIsDragging(true)
    }, [isDragging, isAnalyzing])

    const validateAndSetFile = (selectedFile) => {
        setError(null)
        if (selectedFile && selectedFile.type === 'application/pdf') {
            setFile(selectedFile)
        } else {
            setError('Please upload a valid PDF file.')
        }
    }

    const handleDrop = useCallback((e) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)
        if (isAnalyzing) return

        const droppedFiles = e.dataTransfer.files
        if (droppedFiles?.length > 0) {
            validateAndSetFile(droppedFiles[0])
        }
    }, [isAnalyzing])

    const handleFileInput = (e) => {
        const selectedFiles = e.target.files
        if (selectedFiles?.length > 0) {
            validateAndSetFile(selectedFiles[0])
        }
    }

    const triggerFileInput = () => {
        if (!isAnalyzing) fileInputRef.current?.click()
    }

    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes'
        const k = 1024
        const sizes = ['Bytes', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const removeFile = (e) => {
        e.stopPropagation()
        if (isAnalyzing) return
        setFile(null)
        setError(null)
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }

    const analyzeFile = async () => {
        if (!file) return;
        setIsAnalyzing(true);
        setError(null);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch("http://127.0.0.1:8000/api/convert", {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || "Failed to analyze PDF file");
            }

            const data = await response.json();
            setAnalysisResult(data);
        } catch (err) {
            setError(err.message || 'An unexpected error occurred during analysis.');
        } finally {
            setIsAnalyzing(false);
        }
    }

    const handleReset = () => {
        setAnalysisResult(null);
        setFile(null);
        // when navigating back from dashboard we should also pop the history entry
        if (window.history.state && window.history.state.dashboard) {
            window.history.back();
        }
    }

    // push a history entry when analysis result is shown so browser back works
    useEffect(() => {
        if (analysisResult) {
            // add a dummy state to track dashboard view
            window.history.pushState({ dashboard: true }, 'Analytics');

            const onPop = (evt) => {
                // if user hits back while in dashboard, reset the app
                if (analysisResult) {
                    handleReset();
                }
            };
            window.addEventListener('popstate', onPop);
            return () => window.removeEventListener('popstate', onPop);
        }
    }, [analysisResult]);

    return (
        <div className="app-container">
            <div className="glow-effect"></div>

            <main className={`main-content ${analysisResult ? 'dashboard-mode' : ''}`}>
                {!analysisResult ? (
                    <>
                        <header className="header">
                            <div className="logo-container">
                                <h1 className="title">KTU Result Analyzer</h1>
                                <div className="title-underline"></div>
                            </div>
                            <p className="subtitle">Upload your KTU semester result PDF to dynamically extract everything into an Excel sheet</p>
                        </header>

                        <section
                            className={`upload-card ${isDragging ? 'dragging' : ''} ${file ? 'has-file' : ''} ${isAnalyzing ? 'disabled' : ''}`}
                            onDragEnter={handleDragEnter}
                            onDragLeave={handleDragLeave}
                            onDragOver={handleDragOver}
                            onDrop={handleDrop}
                            onClick={!file && !isAnalyzing ? triggerFileInput : undefined}
                        >
                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileInput}
                                accept=".pdf,application/pdf"
                                className="hidden-input"
                                disabled={isAnalyzing}
                            />

                            {!file ? (
                                <div className="upload-prompt">
                                    <div className="icon-container">
                                        <svg className="upload-icon" xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                            <polyline points="17 8 12 3 7 8"></polyline>
                                            <line x1="12" y1="3" x2="12" y2="15"></line>
                                        </svg>
                                    </div>
                                    <h3 className="prompt-title">Choose a PDF or drag & drop it here</h3>
                                    <p className="prompt-desc">Supports up to 10MB PDF files</p>
                                    <button
                                        className="browse-btn"
                                        onClick={(e) => { e.stopPropagation(); triggerFileInput(); }}
                                        disabled={isAnalyzing}
                                    >
                                        Browse Files
                                    </button>
                                </div>
                            ) : (
                                <div className="file-info-container">
                                    <div className="file-icon">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                            <polyline points="14 2 14 8 20 8"></polyline>
                                            <line x1="16" y1="13" x2="8" y2="13"></line>
                                            <line x1="16" y1="17" x2="8" y2="17"></line>
                                            <polyline points="10 9 9 9 8 9"></polyline>
                                        </svg>
                                    </div>
                                    <div className="file-details">
                                        <p className="file-name" title={file.name}>{file.name}</p>
                                        <p className="file-size">{formatFileSize(file.size)}</p>
                                    </div>
                                    <button
                                        className="remove-btn"
                                        onClick={removeFile}
                                        aria-label="Remove file"
                                        disabled={isAnalyzing}
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <line x1="18" y1="6" x2="6" y2="18"></line>
                                            <line x1="6" y1="6" x2="18" y2="18"></line>
                                        </svg>
                                    </button>
                                </div>
                            )}
                        </section>

                        {error && (
                            <div className="error-message action-enter">
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <line x1="12" y1="8" x2="12" y2="12"></line>
                                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                                </svg>
                                {error}
                            </div>
                        )}

                        {file && (
                            <div className="action-container action-enter">
                                <button
                                    className={`analyze-btn ${isAnalyzing ? 'analyzing' : ''}`}
                                    onClick={analyzeFile}
                                    disabled={isAnalyzing}
                                >
                                    {isAnalyzing ? (
                                        <>
                                            <div className="spinner"></div>
                                            Extracting to Excel...
                                        </>
                                    ) : (
                                        <>
                                            Analyze Results
                                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <line x1="5" y1="12" x2="19" y2="12"></line>
                                                <polyline points="12 5 19 12 12 19"></polyline>
                                            </svg>
                                        </>
                                    )}
                                </button>
                            </div>
                        )}
                    </>
                ) : (
                    <Dashboard data={analysisResult} onReset={handleReset} />
                )}
            </main>
        </div>
    )
}

export default App
