import { Button } from "./ui/button";

export function ConfirmationModal({ 
    isOpen, 
    onClose, 
    onConfirm,
    message 
  }: {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    message: string;
  }) {
    if (!isOpen) return null;
  
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl p-6 max-w-md w-full">
          <h3 className="text-lg font-semibold mb-4">Confirm Action</h3>
          <p className="text-gray-600 mb-6">{message}</p>
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={onConfirm}>Confirm</Button>
          </div>
        </div>
      </div>
    );
  }