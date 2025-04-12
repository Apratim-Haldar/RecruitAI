interface Props {
    children: React.ReactNode;
    onClose?: () => void;
  }
  
  export default function Modal({ children, onClose }: Props) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="relative bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
          {onClose && (
            <button 
              onClick={onClose}
              className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          )}
          {children}
        </div>
      </div>
    );
  }