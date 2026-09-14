/* =========================================================
   LLM GUARDRAILS STUDIO
   Frontend Controller
   Author: Ajim Mujawar
   ========================================================= */

"use strict";

/* =========================================================
   DOM ELEMENTS
   ========================================================= */

const promptInput = document.getElementById("promptInput");
const sendButton = document.getElementById("sendButton");
const charCount = document.getElementById("charCount");

const statusBox = document.getElementById("statusBox");
const securityResult = document.getElementById("securityResult");

const responseBox = document.getElementById("responseBox");
const responseContent = document.getElementById("responseContent");

const totalTime = document.getElementById("totalTime");
const inputTime = document.getElementById("inputTime");
const llmTime = document.getElementById("llmTime");
const outputTime = document.getElementById("outputTime");

const pipelineSteps = document.querySelectorAll(".pipeline-step");

/* =========================================================
   CHARACTER COUNTER
   ========================================================= */

if (promptInput) {

    promptInput.addEventListener("input", () => {

        const length = promptInput.value.length;

        if (charCount) {
            charCount.textContent = `${length} / 8000 characters`;
        }

    });
}

/* =========================================================
   CTRL + ENTER
   ========================================================= */

if (promptInput) {

    promptInput.addEventListener("keydown", (event) => {

        if (event.ctrlKey && event.key === "Enter") {

            event.preventDefault();

            sendPrompt();
        }

    });
}

/* =========================================================
   EXAMPLE PROMPTS
   ========================================================= */

function useExample(text) {

    if (!promptInput) return;

    promptInput.value = text;

    promptInput.dispatchEvent(
        new Event("input")
    );

    promptInput.focus();
}

/* =========================================================
   RESET UI
   ========================================================= */

function resetUI() {

    if (statusBox) {

        statusBox.className = "status-box";

        statusBox.textContent =
            "Ready. Enter a prompt to test the security pipeline.";
    }

    if (securityResult) {

        securityResult.className = "security-result";

        securityResult.innerHTML = "";
    }

    if (responseBox) {

        responseBox.style.display = "none";
    }

    resetPipeline();
}

/* =========================================================
   RESET PIPELINE
   ========================================================= */

function resetPipeline() {

    pipelineSteps.forEach((step) => {

        step.classList.remove(
            "active",
            "success",
            "blocked"
        );

    });
}

/* =========================================================
   UPDATE PIPELINE
   ========================================================= */

function updatePipeline(stages) {

    if (!stages || !Array.isArray(stages)) {
        return;
    }

    resetPipeline();

    stages.forEach((stage, index) => {

        const step = pipelineSteps[index];

        if (!step) return;

        const status = String(
            stage.status || ""
        ).toLowerCase();

        step.classList.add("active");

        if (
            status.includes("success") ||
            status.includes("passed") ||
            status === "ok"
        ) {

            step.classList.add("success");

        } else if (
            status.includes("blocked") ||
            status.includes("failed") ||
            status.includes("error")
        ) {

            step.classList.add("blocked");
        }

    });
}

/* =========================================================
   STATUS MESSAGE
   ========================================================= */

function showStatus(
    message,
    type = ""
) {

    if (!statusBox) return;

    statusBox.className = `status-box ${type}`;

    statusBox.textContent = message;
}

/* =========================================================
   SECURITY RESULT
   ========================================================= */

function showSecurityResult(data) {

    if (!securityResult) return;

    const blocked =
        data.status === "blocked";

    const category =
        data.category || "SAFE";

    const message =
        data.message ||
        "Guardrail validation completed.";

    securityResult.className =
        `security-result ${
            blocked ? "blocked" : "safe"
        }`;

    securityResult.innerHTML = `

        <div class="security-header">

            <div class="security-title">

                <div class="security-icon">
                    ${blocked ? "🛡️" : "✓"}
                </div>

                <div>
                    <strong>
                        ${
                            blocked
                                ? "Security Check Blocked"
                                : "Security Check Passed"
                        }
                    </strong>

                    <span>
                        ${
                            blocked
                                ? "Guardrail intervention"
                                : "Request passed validation"
                        }
                    </span>
                </div>

            </div>

            <div class="security-badge">
                ${category}
            </div>

        </div>

        <div class="security-message">
            ${escapeHTML(message)}
        </div>
    `;

    securityResult.style.display = "block";
}

/* =========================================================
   RESPONSE
   ========================================================= */

function showResponse(data) {

    if (!responseBox || !responseContent) {
        return;
    }

    const response =
        data.response || "";

    if (!response) {

        responseBox.style.display = "none";

        return;
    }

    responseContent.textContent =
        response;

    responseBox.style.display =
        "block";
}

/* =========================================================
   METRICS
   ========================================================= */

function updateMetrics(metrics) {

    if (!metrics) return;

    if (totalTime) {

        totalTime.textContent =
            formatTime(metrics.total_ms);
    }

    if (inputTime) {

        inputTime.textContent =
            formatTime(
                metrics.input_guardrail_ms
            );
    }

    if (llmTime) {

        llmTime.textContent =
            formatTime(metrics.llm_ms);
    }

    if (outputTime) {

        outputTime.textContent =
            formatTime(
                metrics.output_guardrail_ms
            );
    }
}

/* =========================================================
   FORMAT TIME
   ========================================================= */

function formatTime(value) {

    if (
        value === undefined ||
        value === null ||
        Number.isNaN(Number(value))
    ) {

        return "--";
    }

    return `${Number(value).toFixed(1)} ms`;
}

/* =========================================================
   LOADING STATE
   ========================================================= */

function setLoading(isLoading) {

    if (!sendButton) return;

    sendButton.disabled =
        isLoading;

    if (isLoading) {

        sendButton.innerHTML = `
            <span class="loading">
                <span></span>
                <span></span>
                <span></span>
            </span>
            &nbsp; Running Security Pipeline...
        `;

    } else {

        sendButton.innerHTML =
            "🛡️ Send Prompt";
    }
}

/* =========================================================
   SEND PROMPT
   ========================================================= */

async function sendPrompt() {

    if (!promptInput) return;

    const prompt =
        promptInput.value.trim();

    /* -----------------------------------------
       Empty prompt
       ----------------------------------------- */

    if (!prompt) {

        showStatus(
            "Please enter a prompt before sending.",
            "error"
        );

        promptInput.focus();

        return;
    }

    /* -----------------------------------------
       Reset previous result
       ----------------------------------------- */

    resetUI();

    setLoading(true);

    showStatus(
        "Running input guardrails...",
        ""
    );

    try {

        const startTime =
            performance.now();

        /* -----------------------------------------
           API REQUEST
           ----------------------------------------- */

        const response =
            await fetch("/generate", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    prompt: prompt
                })

            });

        /* -----------------------------------------
           HTTP ERROR
           ----------------------------------------- */

        if (!response.ok) {

            throw new Error(
                `Server returned ${response.status}`
            );
        }

        const data =
            await response.json();

        const clientTime =
            performance.now() - startTime;

        /* -----------------------------------------
           UPDATE PIPELINE
           ----------------------------------------- */

        updatePipeline(
            data.stages
        );

        /* -----------------------------------------
           UPDATE METRICS
           ----------------------------------------- */

        updateMetrics(
            data.metrics
        );

        /* -----------------------------------------
           STATUS
           ----------------------------------------- */

        if (data.status === "success") {

            showStatus(
                "✓ Prompt processed successfully. All guardrails passed.",
                "success"
            );

        } else if (
            data.status === "blocked"
        ) {

            showStatus(
                `🛡️ Request blocked by security guardrails: ${
                    data.category || "Security Policy"
                }`,
                "blocked"
            );

        } else {

            showStatus(
                data.message ||
                "An error occurred while processing the request.",
                "error"
            );
        }

        /* -----------------------------------------
           SECURITY RESULT
           ----------------------------------------- */

        showSecurityResult(data);

        /* -----------------------------------------
           RESPONSE
           ----------------------------------------- */

        if (data.status === "success") {

            showResponse(data);

        } else {

            if (responseBox) {
                responseBox.style.display =
                    "none";
            }
        }

        /* -----------------------------------------
           Fallback total time
           ----------------------------------------- */

        if (
            data.metrics &&
            data.metrics.total_ms === undefined
        ) {

            if (totalTime) {

                totalTime.textContent =
                    formatTime(clientTime);
            }
        }

    } catch (error) {

        console.error(
            "Request failed:",
            error
        );

        showStatus(
            `Connection error: ${error.message}`,
            "error"
        );

        resetPipeline();

    } finally {

        setLoading(false);
    }
}

/* =========================================================
   HTML ESCAPE
   ========================================================= */

function escapeHTML(value) {

    const div =
        document.createElement("div");

    div.textContent =
        String(value);

    return div.innerHTML;
}

/* =========================================================
   GLOBAL FUNCTIONS
   ========================================================= */

window.sendPrompt =
    sendPrompt;

window.useExample =
    useExample;

window.resetUI =
    resetUI;