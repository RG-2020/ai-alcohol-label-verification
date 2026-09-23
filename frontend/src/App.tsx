import { useCallback, useState } from "react";
import Cropper, { type Area } from "react-easy-crop";
import "./App.css";


type AppMode =
  | "verify"
  | "scan";


type VerificationDetail = {
  status: string;
  detected_value: string;
};


type VerifyResponse = {
  front_filename?: string;
  back_filename?: string | null;

  status?: string;
  message?: string;

  extracted_text?: string;
  front_ocr_text?: string;
  back_ocr_text?: string;

  overall_result?: string;
  ocr_confidence?: number;
  processing_time_seconds?: number;

  verification_results?: {
    brand_name: VerificationDetail;
    class_type: VerificationDetail;
    alcohol_content: VerificationDetail;
    net_contents: VerificationDetail;
    producer_name: VerificationDetail;
    producer_address: VerificationDetail;
    government_warning: VerificationDetail;
  };

  application_data?: {
    brand_name: string;
    class_type: string;
    alcohol_content: string;
    net_contents: string;
    producer_name: string;
    producer_address: string;
  };

  scan_data?: {
    brand_name?: string | null;
    class_type?: string | null;
    alcohol_content?: string | null;
    net_contents?: string | null;
    producer_name?: string | null;
    producer_address?: string | null;
    government_warning?: string | null;
  };
};


type ChatMessage = {
  sender: "user" | "assistant";
  text: string;
};


function getStatusClass(
  status?: string
) {
  if (status === "MATCH") {
    return "status-badge match";
  }

  if (status === "MISMATCH") {
    return "status-badge mismatch";
  }

  return "status-badge review";
}


function getOverallClass(
  result?: string
) {
  if (result === "PASS") {
    return "overall-badge pass";
  }

  if (
    result ===
    "POTENTIAL MISMATCH"
  ) {
    return "overall-badge mismatch";
  }

  return "overall-badge review";
}


function getConfidenceLabel(
  confidence?: number
) {
  if (
    confidence === undefined
  ) {
    return "";
  }

  if (confidence >= 80) {
    return "HIGH";
  }

  if (confidence >= 60) {
    return "MEDIUM";
  }

  return "LOW";
}


async function createCroppedFile(
  imageSrc: string,
  pixelCrop: Area,
  originalFile: File
): Promise<File> {
  const image = new Image();

  image.src = imageSrc;

  await new Promise<void>(
    (
      resolve,
      reject
    ) => {
      image.onload =
        () => resolve();

      image.onerror =
        () => reject();
    }
  );

  const canvas =
    document.createElement(
      "canvas"
    );

  const context =
    canvas.getContext(
      "2d"
    );

  if (!context) {
    throw new Error(
      "Could not create crop canvas."
    );
  }

  canvas.width =
    pixelCrop.width;

  canvas.height =
    pixelCrop.height;

  context.drawImage(
    image,
    pixelCrop.x,
    pixelCrop.y,
    pixelCrop.width,
    pixelCrop.height,
    0,
    0,
    pixelCrop.width,
    pixelCrop.height
  );

  const blob =
    await new Promise<Blob>(
      (
        resolve,
        reject
      ) => {
        canvas.toBlob(
          result => {
            if (result) {
              resolve(
                result
              );
            } else {
              reject(
                new Error(
                  "Could not create cropped image."
                )
              );
            }
          },
          originalFile.type ||
            "image/jpeg",
          0.95
        );
      }
    );

  return new File(
    [blob],
    `cropped-${originalFile.name}`,
    {
      type:
        originalFile.type ||
        "image/jpeg",
    }
  );
}


function buildChatAnswer(
  question: string,
  result: VerifyResponse | null,
  mode: AppMode
) {
  const q =
    question
      .toLowerCase()
      .trim();

  if (!result) {
    return (
      "Please process a label first so I can explain the result."
    );
  }


  if (
    q.includes("time") ||
    q.includes("speed") ||
    q.includes("seconds") ||
    q.includes("fast")
  ) {
    if (
      result.processing_time_seconds ===
      undefined
    ) {
      return (
        "Processing-time information is not available."
      );
    }

    return (
      `This request took ${result.processing_time_seconds} seconds to process.`
    );
  }


  if (mode === "scan") {
    const scan = result.scan_data;

    const detectedFields = scan
      ? [
          ["Brand Name", scan.brand_name],
          ["Class / Type", scan.class_type],
          ["Alcohol Content", scan.alcohol_content],
          ["Net Contents", scan.net_contents],
          ["Producer / Bottler Name", scan.producer_name],
          ["Producer / Bottler Address / Country of Origin", scan.producer_address],
          ["Government Warning", scan.government_warning],
        ].filter(([, value]) => Boolean(value))
      : [];

    const uncertainFields = scan
      ? [
          ["Brand Name", scan.brand_name],
          ["Class / Type", scan.class_type],
          ["Alcohol Content", scan.alcohol_content],
          ["Net Contents", scan.net_contents],
          ["Producer / Bottler Name", scan.producer_name],
          ["Producer / Bottler Address / Country of Origin", scan.producer_address],
          ["Government Warning", scan.government_warning],
        ]
          .filter(([, value]) =>
            !value ||
            String(value)
              .toLowerCase()
              .includes("not confidently detected")
          )
          .map(([label]) => label)
      : [];

    if (
      q === "why" ||
      q === "why?" ||
      (
        q.includes("why") &&
        (
          q.includes("manual") ||
          q.includes("review") ||
          q.includes("result")
        )
      )
    ) {
      return (
        "Scan Label Only does not assign PASS, MISMATCH, or MANUAL REVIEW REQUIRED. " +
        "It extracts what OCR can read and leaves uncertain fields as 'Not confidently detected'. " +
        `OCR confidence for this scan is ${result.ocr_confidence ?? "not available"}%.`
      );
    }

    if (
      q.includes("which fields need review") ||
      q.includes("fields need review") ||
      q.includes("fields needing review") ||
      q.includes("uncertain fields") ||
      q.includes("not confidently detected")
    ) {
      return uncertainFields.length
        ? `These fields were not confidently detected: ${uncertainFields.join(", ")}.`
        : "All scan fields produced a detected value, but Scan Label Only does not make a compliance decision.";
    }

    if (
      q.includes("confidence") ||
      q.includes("ocr")
    ) {
      const confidence = result.ocr_confidence;

      return confidence === undefined
        ? "OCR confidence information is not available."
        : `OCR confidence is ${confidence}%, which is ${getConfidenceLabel(confidence)}.`;
    }

    if (
      q.includes("what was detected") ||
      q.includes("detected information") ||
      q.includes("summary") ||
      q.includes("summarize")
    ) {
      if (!detectedFields.length) {
        return "No label fields were confidently extracted from this scan.";
      }

      const summary = detectedFields
        .map(([label, value]) => `${label}: ${value}`)
        .join("; ");

      return (
        `Detected information: ${summary}. ` +
        `OCR confidence is ${result.ocr_confidence ?? "not available"}%.`
      );
    }

    if (q.includes("front")) {
      return result.front_ocr_text
        ? `Front-label OCR detected: ${result.front_ocr_text}`
        : "No front-label OCR text was detected.";
    }

    if (q.includes("back")) {
      return result.back_ocr_text
        ? `Back-label OCR detected: ${result.back_ocr_text}`
        : "No back-label OCR text was detected.";
    }

    if (
      q.includes("thanks") ||
      q === "thank you"
    ) {
      return "You're welcome.";
    }

    return (
      "I can summarize the scan, explain OCR confidence, list fields that were not confidently detected, or show the front/back OCR text."
    );
  }


  const verification =
    result.verification_results;


  if (
    q.includes("which fields need review") ||
    q.includes("fields need review") ||
    q.includes("fields needing review")
  ) {
    const fields = result.verification_results;

    if (!fields) {
      return "Field verification information is not available.";
    }

    const needsAttention = [
      ["Brand Name", fields.brand_name.status],
      ["Class / Type", fields.class_type.status],
      ["Alcohol Content", fields.alcohol_content.status],
      ["Net Contents", fields.net_contents.status],
      ["Producer / Bottler Name", fields.producer_name.status],
      ["Producer / Bottler Address / Country of Origin", fields.producer_address.status],
      ["Government Warning", fields.government_warning.status],
    ]
      .filter(([, status]) => status !== "MATCH")
      .map(([label, status]) => `${label} (${status})`);

    return needsAttention.length
      ? `These fields need attention: ${needsAttention.join(", ")}.`
      : "All checked fields matched.";
  }


  if (
    q === "why" ||
    q === "why?" ||
    (
      q.includes("why") &&
      (
        q.includes("manual") ||
        q.includes("review") ||
        q.includes("mismatch")
      )
    )
  ) {
    const reviewFields: string[] =
      [];

    const mismatchFields: string[] =
      [];

    if (verification) {

      if (
        verification.brand_name.status ===
        "REVIEW"
      ) {
        reviewFields.push(
          "Brand Name"
        );
      }

      if (
        verification.class_type.status ===
        "REVIEW"
      ) {
        reviewFields.push(
          "Class / Type"
        );
      }

      if (
        verification.alcohol_content.status ===
        "REVIEW"
      ) {
        reviewFields.push(
          "Alcohol Content"
        );
      }

      if (
        verification.net_contents.status ===
        "REVIEW"
      ) {
        reviewFields.push(
          "Net Contents"
        );
      }

      if (
        verification.producer_name.status ===
        "REVIEW"
      ) {
        reviewFields.push(
          "Producer / Bottler Name"
        );
      }

      if (
        verification.producer_address.status ===
        "REVIEW"
      ) {
        reviewFields.push(
          "Producer / Bottler Address / Country of Origin"
        );
      }

      if (
        verification.government_warning.status ===
        "REVIEW"
      ) {
        reviewFields.push(
          "Government Warning"
        );
      }
    }


    if (verification) {
      if (verification.brand_name.status === "MISMATCH") {
        mismatchFields.push("Brand Name");
      }

      if (verification.class_type.status === "MISMATCH") {
        mismatchFields.push("Class / Type");
      }

      if (verification.alcohol_content.status === "MISMATCH") {
        mismatchFields.push("Alcohol Content");
      }

      if (verification.net_contents.status === "MISMATCH") {
        mismatchFields.push("Net Contents");
      }

      if (verification.producer_name.status === "MISMATCH") {
        mismatchFields.push("Producer / Bottler Name");
      }

      if (verification.producer_address.status === "MISMATCH") {
        mismatchFields.push(
          "Producer / Bottler Address / Country of Origin"
        );
      }

      if (verification.government_warning.status === "MISMATCH") {
        mismatchFields.push("Government Warning");
      }
    }


    if (
      mismatchFields.length > 0
    ) {
      return (
        `LabelGuard found a potential mismatch in: ${mismatchFields.join(
          ", "
        )}. ` +
        (
          reviewFields.length > 0
            ? `It also needs manual review for: ${reviewFields.join(", ")}.`
            : "The remaining fields did not require manual review."
        )
      );
    }


    if (
      reviewFields.length === 0
    ) {
      return (
        `The overall result is ${
          result.overall_result ||
          "not available"
        }.`
      );
    }


    return (
      `The result requires manual review because OCR confidence is ${
        result.ocr_confidence ??
        "unknown"
      }% and the system could not confidently verify: ${reviewFields.join(
        ", "
      )}.`
    );
  }


  if (
    q.includes(
      "i don't think so"
    ) ||
    q.includes(
      "i dont think so"
    ) ||
    q.includes(
      "that's wrong"
    ) ||
    q.includes(
      "thats wrong"
    ) ||
    q.includes(
      "not correct"
    )
  ) {
    return (
      "The reviewer may be correct. LabelGuard AI does not make the final compliance decision. " +
      "If OCR misses information that is clearly visible on the label, the image should be manually reviewed."
    );
  }


  if (
    q.includes("thanks") ||
    q === "thank you"
  ) {
    return (
      "You're welcome. You can ask me about any verification field."
    );
  }


  if (
    q === "hello" ||
    q === "hi" ||
    q === "hey"
  ) {
    return (
      "Hello. I can explain this label-verification result."
    );
  }


  if (
    q.includes("overall") ||
    q.includes("result")
  ) {
    return (
      `The overall result is ${
        result.overall_result ||
        "not available"
      }. OCR confidence is ${
        result.ocr_confidence ??
        "not available"
      }%.`
    );
  }


  if (
    q.includes("confidence") ||
    q.includes("ocr quality")
  ) {
    const confidence =
      result.ocr_confidence;

    if (
      confidence === undefined
    ) {
      return (
        "OCR confidence information is not available."
      );
    }


    return (
      `OCR confidence is ${confidence}%, which is ${getConfidenceLabel(
        confidence
      )}.`
    );
  }


  if (
    q.includes("brand")
  ) {
    const field =
      verification?.brand_name;

    return field
      ? `Brand Name status: ${field.status}. Detected value: ${field.detected_value}.`
      : "Brand Name verification information is not available.";
  }


  if (
    q.includes("class") ||
    q.includes("type")
  ) {
    const field =
      verification?.class_type;

    return field
      ? `Class / Type status: ${field.status}. Detected value: ${field.detected_value}.`
      : "Class / Type verification information is not available.";
  }


  if (
    q.includes("alcohol") ||
    q.includes("abv") ||
    q.includes("%")
  ) {
    const field =
      verification?.alcohol_content;

    return field
      ? `Alcohol Content status: ${field.status}. Detected value: ${field.detected_value}.`
      : "Alcohol Content verification information is not available.";
  }


  if (
    q.includes("net") ||
    q.includes("volume") ||
    q.includes("ml")
  ) {
    const field =
      verification?.net_contents;

    return field
      ? `Net Contents status: ${field.status}. Detected value: ${field.detected_value}.`
      : "Net Contents verification information is not available.";
  }


  if (
    q.includes("address") ||
    q.includes("country") ||
    q.includes("origin")
  ) {
    const field =
      verification?.producer_address;

    return field
      ? `Producer / Bottler Address / Country of Origin status: ${field.status}. Detected value: ${field.detected_value}.`
      : "Producer address / country information is not available.";
  }


  if (
    q.includes("producer") ||
    q.includes("bottler")
  ) {
    const field =
      verification?.producer_name;

    return field
      ? `Producer / Bottler Name status: ${field.status}. Detected value: ${field.detected_value}.`
      : "Producer / Bottler information is not available.";
  }


  if (
    q.includes("government") ||
    q.includes("warning")
  ) {
    const field =
      verification?.government_warning;

    return field
      ? `Government Warning status: ${field.status}. Detected: ${field.detected_value}.`
      : "Government Warning information is not available.";
  }


  if (
    q.includes("front")
  ) {
    return (
      result.front_ocr_text
        ? `Front-label OCR detected: ${result.front_ocr_text}`
        : "No front-label OCR text was detected."
    );
  }


  if (
    q.includes("back")
  ) {
    return (
      result.back_ocr_text
        ? `Back-label OCR detected: ${result.back_ocr_text}`
        : "No back-label OCR text was detected."
    );
  }


  if (
    q.includes("summary") ||
    q.includes("summarize")
  ) {
    return (
      `Overall result: ${
        result.overall_result ||
        "not available"
      }. OCR confidence: ${
        result.ocr_confidence ??
        "not available"
      }%. Processing time: ${
        result.processing_time_seconds ??
        "not available"
      } seconds.`
    );
  }


  return (
    "I can explain the overall result, OCR confidence, processing time, brand, class/type, alcohol content, net contents, producer information, country of origin, government warning, or manual-review result."
  );
}


function VerificationRow({
  label,
  detail,
}: {
  label: string;
  detail: VerificationDetail;
}) {
  return (
    <p>
      <strong>
        {label}:
      </strong>{" "}

      <span
        className={
          getStatusClass(
            detail.status
          )
        }
      >
        {detail.status}
      </span>

      <br />

      <small>
        Detected:{" "}
        {
          detail.detected_value
        }
      </small>
    </p>
  );
}


function App() {
  const [
    mode,
    setMode,
  ] =
    useState<AppMode>(
      "verify"
    );


  const [
    file,
    setFile,
  ] =
    useState<File | null>(
      null
    );

  const [
    previewUrl,
    setPreviewUrl,
  ] =
    useState("");


  const [
    backFile,
    setBackFile,
  ] =
    useState<File | null>(
      null
    );

  const [
    backPreviewUrl,
    setBackPreviewUrl,
  ] =
    useState("");


  const [
    crop,
    setCrop,
  ] =
    useState({
      x: 0,
      y: 0,
    });

  const [
    zoom,
    setZoom,
  ] =
    useState(1);

  const [
    croppedAreaPixels,
    setCroppedAreaPixels,
  ] =
    useState<Area | null>(
      null
    );

  const [
    useManualCrop,
    setUseManualCrop,
  ] =
    useState(false);


  const [
    backCrop,
    setBackCrop,
  ] =
    useState({
      x: 0,
      y: 0,
    });

  const [
    backZoom,
    setBackZoom,
  ] =
    useState(1);

  const [
    backCroppedAreaPixels,
    setBackCroppedAreaPixels,
  ] =
    useState<Area | null>(
      null
    );

  const [
    useBackManualCrop,
    setUseBackManualCrop,
  ] =
    useState(false);


  const [
    brandName,
    setBrandName,
  ] =
    useState("");

  const [
    classType,
    setClassType,
  ] =
    useState("");

  const [
    alcoholContent,
    setAlcoholContent,
  ] =
    useState("");

  const [
    netContents,
    setNetContents,
  ] =
    useState("");

  const [
    producerName,
    setProducerName,
  ] =
    useState("");

  const [
    producerAddress,
    setProducerAddress,
  ] =
    useState("");


  const [
    result,
    setResult,
  ] =
    useState<VerifyResponse | null>(
      null
    );

  const [
    loading,
    setLoading,
  ] =
    useState(false);

  const [
    error,
    setError,
  ] =
    useState("");


  const [
    chatInput,
    setChatInput,
  ] =
    useState("");

  const [
    chatMessages,
    setChatMessages,
  ] =
    useState<ChatMessage[]>(
      []
    );


  const onCropComplete =
    useCallback(
      (
        _croppedArea: Area,
        croppedPixels: Area
      ) => {
        setCroppedAreaPixels(
          croppedPixels
        );
      },
      []
    );


  const onBackCropComplete =
    useCallback(
      (
        _croppedArea: Area,
        croppedPixels: Area
      ) => {
        setBackCroppedAreaPixels(
          croppedPixels
        );
      },
      []
    );


  const handleModeChange = (
    newMode: AppMode
  ) => {
    setMode(
      newMode
    );

    setResult(
      null
    );

    setError(
      ""
    );

    setChatMessages(
      []
    );
  };


  const handleAskChat = (
    suggestedQuestion?: string
  ) => {
    const question = (
      suggestedQuestion ??
      chatInput
    ).trim();

    // Give the user feedback if Ask is clicked with an empty question.
    if (!question) {
      setChatMessages(
        previous => [
          ...previous,
          {
            sender: "assistant",
            text: "Type a question first, or use one of the quick questions below.",
          },
        ]
      );
      return;
    }

    try {
      const answer =
        buildChatAnswer(
          question,
          result,
          mode
        );

      setChatMessages(
        previous => [
          ...previous,
          {
            sender: "user",
            text: question,
          },
          {
            sender: "assistant",
            text: answer,
          },
        ]
      );

      setChatInput("");
    } catch (chatError) {
      console.error(
        "LabelGuard chat error:",
        chatError
      );

      setChatMessages(
        previous => [
          ...previous,
          {
            sender: "user",
            text: question,
          },
          {
            sender: "assistant",
            text: "I could not explain that result. Please try a shorter question such as 'Why this result?'",
          },
        ]
      );
    }
  };

  const handleProcess =
    async () => {
      setResult(null);
      setError("");
      setChatMessages([]);

      if (!file) {
        setError(
          "Please choose a front label image first."
        );
        return;
      }


      if (
        mode === "verify"
      ) {
        if (!brandName.trim()) {
          setError(
            "Please enter the Brand Name."
          );
          return;
        }

        if (!classType.trim()) {
          setError(
            "Please enter the Class / Type."
          );
          return;
        }

        if (!alcoholContent.trim()) {
          setError(
            "Please enter the Alcohol Content."
          );
          return;
        }

        if (!netContents.trim()) {
          setError(
            "Please enter the Net Contents."
          );
          return;
        }

        if (!producerName.trim()) {
          setError(
            "Please enter the Producer / Bottler Name."
          );
          return;
        }

        if (!producerAddress.trim()) {
          setError(
            "Please enter the Producer / Bottler Address / Country of Origin."
          );
          return;
        }
      }


      setLoading(
        true
      );


      try {
        let frontFileToSend =
          file;


        if (
          useManualCrop &&
          previewUrl &&
          croppedAreaPixels
        ) {
          frontFileToSend =
            await createCroppedFile(
              previewUrl,
              croppedAreaPixels,
              file
            );
        }


        let backFileToSend =
          backFile;


        if (
          backFile &&
          useBackManualCrop &&
          backPreviewUrl &&
          backCroppedAreaPixels
        ) {
          backFileToSend =
            await createCroppedFile(
              backPreviewUrl,
              backCroppedAreaPixels,
              backFile
            );
        }


        const formData =
          new FormData();


        formData.append(
          "front_image",
          frontFileToSend
        );


        if (
          backFileToSend
        ) {
          formData.append(
            "back_image",
            backFileToSend
          );
        }


        let endpoint =
          "http://127.0.0.1:8000/verify";


        if (
          mode === "verify"
        ) {
          formData.append(
            "brand_name",
            brandName
          );

          formData.append(
            "class_type",
            classType
          );

          formData.append(
            "alcohol_content",
            alcoholContent
          );

          formData.append(
            "net_contents",
            netContents
          );

          formData.append(
            "producer_name",
            producerName
          );

          formData.append(
            "producer_address",
            producerAddress
          );

          formData.append(
            "use_center_crop",
            "false"
          );

        } else {
          endpoint =
            "http://127.0.0.1:8000/scan";

          formData.append(
            "use_center_crop",
            "false"
          );
        }


        const response =
          await fetch(
            endpoint,
            {
              method: "POST",
              body: formData,
            }
          );


        if (!response.ok) {
          let message =
            "Request failed.";

          try {
            const errorData =
              await response.json();

            if (
              typeof
                errorData.detail ===
              "string"
            ) {
              message =
                errorData.detail;
            } else if (
              errorData.detail
            ) {
              message =
                JSON.stringify(
                  errorData.detail
                );
            }

          } catch {
            message =
              `Request failed with status ${response.status}.`;
          }

          throw new Error(
            message
          );
        }


        const data:
          VerifyResponse =
          await response.json();


        setResult(
          data
        );


        if (
          mode === "verify"
        ) {
          setChatMessages([
            {
              sender:
                "assistant",

              text:
                `Verification completed. ` +
                `Overall result: ${
                  data.overall_result ||
                  "not available"
                }. ` +
                `OCR confidence: ${
                  data.ocr_confidence ??
                  "not available"
                }%. ` +
                `Processing time: ${
                  data.processing_time_seconds ??
                  "not available"
                } seconds.`,
            },
          ]);

        } else {
          setChatMessages([
            {
              sender:
                "assistant",

              text:
                `Label scan completed. ` +
                `OCR confidence: ${
                  data.ocr_confidence ??
                  "not available"
                }%. ` +
                `Processing time: ${
                  data.processing_time_seconds ??
                  "not available"
                } seconds.`,
            },
          ]);
        }


      } catch (err) {

        console.error(
          err
        );

        if (
          err instanceof Error
        ) {
          setError(
            err.message
          );

        } else {
          setError(
            "Could not process the label."
          );
        }

      } finally {
        setLoading(
          false
        );
      }
    };


  const handleReset = () => {
    setFile(null);
    setBackFile(null);

    setPreviewUrl("");
    setBackPreviewUrl("");

    setCrop({
      x: 0,
      y: 0,
    });

    setBackCrop({
      x: 0,
      y: 0,
    });

    setZoom(1);
    setBackZoom(1);

    setCroppedAreaPixels(
      null
    );

    setBackCroppedAreaPixels(
      null
    );

    setUseManualCrop(
      false
    );

    setUseBackManualCrop(
      false
    );

    setBrandName("");
    setClassType("");
    setAlcoholContent("");
    setNetContents("");
    setProducerName("");
    setProducerAddress("");

    setResult(null);
    setError("");
    setChatInput("");
    setChatMessages([]);
  };


  return (
    <div className="app">

      <div className="watermark">
        LabelGuard AI
      </div>


      <div className="container">

        <h1>
          LabelGuard AI
        </h1>


        <p className="creator">
          Alcohol Label Verification Prototype by Rahel S. Gizaw
        </p>


        <p className="subtitle">
          Scan alcohol labels or compare them against application information.
        </p>


        <div className="card">

          <h3>
            Choose Verification Mode
          </h3>


          <div className="mode-selector">

            <button
              type="button"
              className={
                mode === "verify"
                  ? "mode-button active"
                  : "mode-button"
              }
              onClick={() =>
                handleModeChange(
                  "verify"
                )
              }
            >
              Verify Against Application
            </button>


            <button
              type="button"
              className={
                mode === "scan"
                  ? "mode-button active"
                  : "mode-button"
              }
              onClick={() =>
                handleModeChange(
                  "scan"
                )
              }
            >
              Scan Label Only
            </button>

          </div>


          {mode === "verify" ? (
            <p className="mode-description">
              Upload the label and enter the application information.
              LabelGuard AI will compare the two.
            </p>
          ) : (
            <p className="mode-description">
              Upload the label without entering application information.
              LabelGuard AI will extract readable information from the label.
            </p>
          )}


          <h3>
            1. Upload Label Images
          </h3>


          <label>
            Upload Front Label Image
          </label>


          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const selectedFile =
                e.target.files?.[0] ||
                null;

              setFile(
                selectedFile
              );

              setResult(
                null
              );

              if (
                selectedFile
              ) {
                setPreviewUrl(
                  URL.createObjectURL(
                    selectedFile
                  )
                );
              } else {
                setPreviewUrl(
                  ""
                );
              }
            }}
          />


          {file && (
            <p className="file-name">
              Front label:{" "}
              <strong>
                {file.name}
              </strong>
            </p>
          )}


          <label>
            Upload Back Label Image{" "}
            <span
              style={{
                fontWeight: 400,
              }}
            >
              (optional)
            </span>
          </label>


          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const selected =
                e.target.files?.[0] ||
                null;

              setBackFile(
                selected
              );

              setResult(
                null
              );

              if (
                selected
              ) {
                setBackPreviewUrl(
                  URL.createObjectURL(
                    selected
                  )
                );

              } else {
                setBackPreviewUrl(
                  ""
                );
              }
            }}
          />


          {backFile && (
            <p className="file-name">
              Back label:{" "}
              <strong>
                {backFile.name}
              </strong>
            </p>
          )}


          {(previewUrl ||
            backPreviewUrl) && (
            <>

              <h3>
                2. Select Label Areas
              </h3>


              <div className="label-preview-grid">

                <div className="label-panel">

                  <h3>
                    Front Label
                  </h3>


                  {previewUrl ? (
                    <>
                      <p>
                        Move and zoom the front label if you want to use a selected area.
                      </p>


                      <div className="crop-container">

                        <Cropper
                          image={
                            previewUrl
                          }
                          crop={
                            crop
                          }
                          zoom={
                            zoom
                          }
                          aspect={
                            4 / 3
                          }
                          onCropChange={
                            setCrop
                          }
                          onZoomChange={
                            setZoom
                          }
                          onCropComplete={
                            onCropComplete
                          }
                        />

                      </div>


                      <label>
                        Front Label Zoom
                      </label>


                      <input
                        type="range"
                        min={1}
                        max={4}
                        step={0.1}
                        value={
                          zoom
                        }
                        onChange={(e) =>
                          setZoom(
                            Number(
                              e.target.value
                            )
                          )
                        }
                      />


                      <label className="crop-option">

                        <input
                          type="checkbox"
                          checked={
                            useManualCrop
                          }
                          onChange={(e) =>
                            setUseManualCrop(
                              e.target.checked
                            )
                          }
                        />

                        Use selected front label area for OCR

                      </label>

                    </>
                  ) : (
                    <p>
                      No front label selected.
                    </p>
                  )}

                </div>


                <div className="label-panel">

                  <h3>
                    Back Label
                  </h3>


                  {backPreviewUrl ? (
                    <>
                      <p>
                        Move and zoom the back label if you want to use a selected area.
                      </p>


                      <div className="crop-container">

                        <Cropper
                          image={
                            backPreviewUrl
                          }
                          crop={
                            backCrop
                          }
                          zoom={
                            backZoom
                          }
                          aspect={
                            4 / 3
                          }
                          onCropChange={
                            setBackCrop
                          }
                          onZoomChange={
                            setBackZoom
                          }
                          onCropComplete={
                            onBackCropComplete
                          }
                        />

                      </div>


                      <label>
                        Back Label Zoom
                      </label>


                      <input
                        type="range"
                        min={1}
                        max={4}
                        step={0.1}
                        value={
                          backZoom
                        }
                        onChange={(e) =>
                          setBackZoom(
                            Number(
                              e.target.value
                            )
                          )
                        }
                      />


                      <label className="crop-option">

                        <input
                          type="checkbox"
                          checked={
                            useBackManualCrop
                          }
                          onChange={(e) =>
                            setUseBackManualCrop(
                              e.target.checked
                            )
                          }
                        />

                        Use selected back label area for OCR

                      </label>

                    </>
                  ) : (
                    <p>
                      No back label selected.
                    </p>
                  )}

                </div>

              </div>

            </>
          )}


          {mode === "verify" && (
            <>

              <h3>
                3. Application Information
              </h3>


              <label>
                Brand Name
              </label>

              <input
                type="text"
                value={
                  brandName
                }
                onChange={(e) =>
                  setBrandName(
                    e.target.value
                  )
                }
              />


              <label>
                Class / Type
              </label>

              <input
                type="text"
                value={
                  classType
                }
                onChange={(e) =>
                  setClassType(
                    e.target.value
                  )
                }
              />


              <label>
                Alcohol Content
              </label>

              <input
                type="text"
                value={
                  alcoholContent
                }
                onChange={(e) =>
                  setAlcoholContent(
                    e.target.value
                  )
                }
              />


              <label>
                Net Contents
              </label>

              <input
                type="text"
                value={
                  netContents
                }
                onChange={(e) =>
                  setNetContents(
                    e.target.value
                  )
                }
              />


              <label>
                Producer / Bottler Name
              </label>

              <input
                type="text"
                value={
                  producerName
                }
                onChange={(e) =>
                  setProducerName(
                    e.target.value
                  )
                }
              />


              <label>
                Producer / Bottler Address / Country of Origin
              </label>

              <input
                type="text"
                value={
                  producerAddress
                }
                onChange={(e) =>
                  setProducerAddress(
                    e.target.value
                  )
                }
              />

            </>
          )}


          <button
            type="button"
            onClick={
              handleProcess
            }
            disabled={
              loading
            }
          >
            {
              loading
                ? (
                    mode === "verify"
                      ? "Verifying Labels..."
                      : "Scanning Labels..."
                  )
                : (
                    mode === "verify"
                      ? "Verify Labels"
                      : "Scan Labels"
                  )
            }
          </button>


          {error && (
            <p className="error-message">
              {error}
            </p>
          )}


          {result && (
            <div className="result-box">

              <h2>
                {
                  mode === "verify"
                    ? "Verification Result"
                    : "Label Scan Result"
                }
              </h2>


              {mode === "verify" &&
                result.overall_result && (
                <div className="overall-result">

                  <strong>
                    Overall Result:
                  </strong>{" "}

                  <span
                    className={
                      getOverallClass(
                        result.overall_result
                      )
                    }
                  >
                    {
                      result.overall_result
                    }
                  </span>

                </div>
              )}


              {result.ocr_confidence !==
                undefined && (
                <p>
                  <strong>
                    OCR Confidence:
                  </strong>{" "}

                  {
                    result.ocr_confidence
                  }
                  % —{" "}

                  <strong>
                    {
                      getConfidenceLabel(
                        result.ocr_confidence
                      )
                    }
                  </strong>
                </p>
              )}


              {result.processing_time_seconds !==
                undefined && (
                <p>
                  <strong>
                    Processing Time:
                  </strong>{" "}

                  {
                    result.processing_time_seconds
                  }{" "}
                  seconds
                </p>
              )}


              <p>
                <strong>
                  Front File:
                </strong>{" "}
                {
                  result.front_filename
                }
              </p>


              {result.back_filename && (
                <p>
                  <strong>
                    Back File:
                  </strong>{" "}
                  {
                    result.back_filename
                  }
                </p>
              )}


              <p>
                <strong>
                  Status:
                </strong>{" "}
                {
                  result.status
                }
              </p>


              <p>
                <strong>
                  Message:
                </strong>{" "}
                {
                  result.message
                }
              </p>


              {mode === "verify" &&
                result.application_data && (
                <>

                  <h3>
                    Application Information
                  </h3>

                  <p>
                    <strong>
                      Brand Name:
                    </strong>{" "}
                    {
                      result.application_data.brand_name
                    }
                  </p>

                  <p>
                    <strong>
                      Class / Type:
                    </strong>{" "}
                    {
                      result.application_data.class_type
                    }
                  </p>

                  <p>
                    <strong>
                      Alcohol Content:
                    </strong>{" "}
                    {
                      result.application_data.alcohol_content
                    }
                  </p>

                  <p>
                    <strong>
                      Net Contents:
                    </strong>{" "}
                    {
                      result.application_data.net_contents
                    }
                  </p>

                  <p>
                    <strong>
                      Producer / Bottler Name:
                    </strong>{" "}
                    {
                      result.application_data.producer_name
                    }
                  </p>

                  <p>
                    <strong>
                      Producer / Bottler Address / Country of Origin:
                    </strong>{" "}
                    {
                      result.application_data.producer_address
                    }
                  </p>

                </>
              )}


              {mode === "verify" &&
                result.verification_results && (
                <>

                  <h3>
                    Field Verification
                  </h3>


                  <VerificationRow
                    label="Brand Name"
                    detail={
                      result.verification_results.brand_name
                    }
                  />


                  <VerificationRow
                    label="Class / Type"
                    detail={
                      result.verification_results.class_type
                    }
                  />


                  <VerificationRow
                    label="Alcohol Content"
                    detail={
                      result.verification_results.alcohol_content
                    }
                  />


                  <VerificationRow
                    label="Net Contents"
                    detail={
                      result.verification_results.net_contents
                    }
                  />


                  <VerificationRow
                    label="Producer / Bottler Name"
                    detail={
                      result.verification_results.producer_name
                    }
                  />


                  <VerificationRow
                    label="Producer / Bottler Address / Country of Origin"
                    detail={
                      result.verification_results.producer_address
                    }
                  />


                  <VerificationRow
                    label="Government Warning"
                    detail={
                      result.verification_results.government_warning
                    }
                  />

                </>
              )}


              {mode === "scan" &&
                result.scan_data && (
                <>

                  <h3>
                    Detected Label Information
                  </h3>


                  <p>
                    <strong>
                      Brand Name:
                    </strong>{" "}
                    {
                      result.scan_data.brand_name ||
                      "Not confidently detected"
                    }
                  </p>


                  <p>
                    <strong>
                      Class / Type:
                    </strong>{" "}
                    {
                      result.scan_data.class_type ||
                      "Not confidently detected"
                    }
                  </p>


                  <p>
                    <strong>
                      Alcohol Content:
                    </strong>{" "}
                    {
                      result.scan_data.alcohol_content ||
                      "Not confidently detected"
                    }
                  </p>


                  <p>
                    <strong>
                      Net Contents:
                    </strong>{" "}
                    {
                      result.scan_data.net_contents ||
                      "Not confidently detected"
                    }
                  </p>


                  <p>
                    <strong>
                      Producer / Bottler Name:
                    </strong>{" "}
                    {
                      result.scan_data.producer_name ||
                      "Not confidently detected"
                    }
                  </p>


                  <p>
                    <strong>
                      Producer / Bottler Address / Country of Origin:
                    </strong>{" "}
                    {
                      result.scan_data.producer_address ||
                      "Not confidently detected"
                    }
                  </p>


                  <p>
                    <strong>
                      Government Warning:
                    </strong>{" "}
                    {
                      result.scan_data.government_warning ||
                      "Not confidently detected"
                    }
                  </p>

                </>
              )}


              {result.front_ocr_text && (
                <>

                  <h3>
                    Front Label OCR
                  </h3>

                  <pre className="ocr-text">
                    {
                      result.front_ocr_text
                    }
                  </pre>

                </>
              )}


              {result.back_ocr_text && (
                <>

                  <h3>
                    Back Label OCR
                  </h3>

                  <pre className="ocr-text">
                    {
                      result.back_ocr_text
                    }
                  </pre>

                </>
              )}


              <h3>
                Combined OCR Extracted Text
              </h3>

              <pre className="ocr-text">
                {
                  result.extracted_text ||
                  "No text detected in the images."
                }
              </pre>


              <div className="chat-box">

                <h3>
                  Ask LabelGuard AI
                </h3>


                <p className="chat-description">
                  {
                    mode === "verify"
                      ? "Ask questions about this verification result."
                      : "Ask questions about the scanned label."
                  }
                </p>


                <div className="chat-messages">

                  {chatMessages.map(
                    (
                      message,
                      index
                    ) => (
                      <div
                        key={index}
                        className={
                          message.sender ===
                          "user"
                            ? "chat-message user-message"
                            : "chat-message assistant-message"
                        }
                      >

                        <strong>
                          {
                            message.sender ===
                            "user"
                              ? "You"
                              : "LabelGuard AI"
                          }
                          :
                        </strong>{" "}

                        {
                          message.text
                        }

                      </div>
                    )
                  )}

                </div>


                <div
                  className="chat-input-row"
                  style={{
                    display: "flex",
                    gap: "10px",
                    alignItems: "stretch",
                    width: "100%",
                    position: "relative",
                    zIndex: 5,
                  }}
                >

                  <textarea
                    placeholder={
                      mode === "verify"
                        ? "Type a question about this verification..."
                        : "Type a question about this label scan..."
                    }
                    value={
                      chatInput
                    }
                    onChange={(e) => {
                      setChatInput(
                        e.target.value
                      );
                    }}
                    onKeyDown={(e) => {
                      if (
                        e.key === "Enter" &&
                        !e.shiftKey
                      ) {
                        e.preventDefault();
                        handleAskChat();
                      }
                    }}
                    aria-label="Ask LabelGuard AI"
                    rows={2}
                    style={{
                      flex: 1,
                      width: "100%",
                      minWidth: 0,
                      minHeight: "52px",
                      padding: "12px 14px",
                      border: "1px solid #94a3b8",
                      borderRadius: "8px",
                      background: "#ffffff",
                      color: "#111827",
                      fontSize: "16px",
                      lineHeight: 1.4,
                      resize: "vertical",
                      pointerEvents: "auto",
                      position: "relative",
                      zIndex: 6,
                      opacity: 1,
                      cursor: "text",
                    }}
                  />


                  <button
                    type="button"
                    onClick={() =>
                      handleAskChat()
                    }
                    style={{
                      width: "auto",
                      minWidth: "82px",
                      padding: "0 18px",
                      position: "relative",
                      zIndex: 6,
                      pointerEvents: "auto",
                    }}
                  >
                    Ask
                  </button>

                </div>


                <div className="chat-quick-actions">

                  {mode === "verify" ? (
                    <>
                      <button
                        type="button"
                        onClick={() =>
                          handleAskChat(
                            "Why is this result manual review?"
                          )
                        }
                      >
                        Why this result?
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          handleAskChat(
                            "What is the OCR confidence?"
                          )
                        }
                      >
                        Explain OCR confidence
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          handleAskChat(
                            "Which fields need review?"
                          )
                        }
                      >
                        Fields needing review
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() =>
                          handleAskChat(
                            "Summarize this scan"
                          )
                        }
                      >
                        Summarize scan
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          handleAskChat(
                            "What is the OCR confidence?"
                          )
                        }
                      >
                        Explain OCR confidence
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          handleAskChat(
                            "Which fields were not confidently detected?"
                          )
                        }
                      >
                        Uncertain fields
                      </button>
                    </>
                  )}

                </div>

              </div>


              <button
                type="button"
                className="reset-button"
                onClick={
                  handleReset
                }
              >
                Start New Verification
              </button>

            </div>
          )}

        </div>

      </div>

    </div>
  );
}


export default App;